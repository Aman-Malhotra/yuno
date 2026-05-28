"""Tool executor — turns a tool definition + inputs into a recorded execution.

Responsibilities:

1. Resolve `{{input.x}}` / `{{secrets.x}}` / `{{agent.id}}` / `{{workflow.run_id}}`
   placeholders inside the tool's config (URL, headers, body).
2. Apply per-tool guardrails (allowed/blocked domains, approval gate).
3. Dispatch via the right backend: builtin / http / messaging / agent_handoff /
   webhook.
4. Apply retry + timeout + fallback policy.
5. Persist a `ToolExecution` row + `ToolExecutionLog` lines so the runs UI
   can show what happened.

The executor never raises — it always finishes by writing a terminal
status to the execution row.
"""

from __future__ import annotations

import asyncio
import re
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

import httpx
import structlog

from app.modules.tools.builtins import (
    BuiltinContext,
    BuiltinResult,
    get_builtin,
    run_builtin,
)
from app.modules.tools.models import Tool, ToolExecution
from app.modules.tools.repository import ToolRepository

log = structlog.get_logger("tools.executor")


# ──────────────────────────────────────────────────────────────────────
# Public dispatch context — what the executor needs to know about the
# caller. The service layer constructs this.
# ──────────────────────────────────────────────────────────────────────


class DispatchContext:
    """Lightweight runtime context for a single tool invocation."""

    __slots__ = (
        "workspace_id",
        "agent_id",
        "run_id",
        "run_node_id",
        "user_id",
        "secrets",
    )

    def __init__(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID | None = None,
        run_id: UUID | None = None,
        run_node_id: UUID | None = None,
        user_id: UUID | None = None,
        secrets: Mapping[str, str] | None = None,
    ) -> None:
        self.workspace_id = workspace_id
        self.agent_id = agent_id
        self.run_id = run_id
        self.run_node_id = run_node_id
        self.user_id = user_id
        self.secrets: dict[str, str] = dict(secrets or {})


# ──────────────────────────────────────────────────────────────────────
# Placeholder resolution — handlebar-style {{namespace.key}}
# ──────────────────────────────────────────────────────────────────────


_PLACEHOLDER = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z0-9_]+)+)\s*\}\}")


def _lookup(path: str, env: Mapping[str, Mapping[str, Any]]) -> Any:
    """Resolve `namespace.key.subkey` against the env. Missing → empty string."""

    parts = path.split(".")
    head, *rest = parts
    node: Any = env.get(head, {})
    for part in rest:
        if isinstance(node, Mapping):
            node = node.get(part)
        else:
            return ""
        if node is None:
            return ""
    return node


def render(value: Any, env: Mapping[str, Mapping[str, Any]]) -> Any:
    """Recursively resolve `{{...}}` placeholders inside strings/lists/dicts.

    Whole-value substitution (when a string is *only* a placeholder) preserves
    the underlying type — e.g. `"{{input.count}}"` returns an int.
    """

    if isinstance(value, str):
        match = _PLACEHOLDER.fullmatch(value.strip())
        if match is not None:
            return _lookup(match.group(1), env)
        return _PLACEHOLDER.sub(lambda m: str(_lookup(m.group(1), env) or ""), value)
    if isinstance(value, list):
        return [render(item, env) for item in value]
    if isinstance(value, dict):
        return {k: render(v, env) for k, v in value.items()}
    return value


# ──────────────────────────────────────────────────────────────────────
# Guardrail enforcement
# ──────────────────────────────────────────────────────────────────────


class GuardrailViolation(Exception):
    pass


def _enforce_domain_guardrails(url: str | None, guardrails: Mapping[str, Any]) -> None:
    if not url:
        return
    host = (urlparse(url).hostname or "").lower()
    allowed = [d.lower() for d in guardrails.get("allowed_domains", []) or []]
    blocked = [d.lower() for d in guardrails.get("blocked_domains", []) or []]
    if allowed and not any(host == d or host.endswith("." + d) for d in allowed):
        raise GuardrailViolation(f"host {host!r} is not in allowed_domains")
    if any(host == d or host.endswith("." + d) for d in blocked):
        raise GuardrailViolation(f"host {host!r} is blocked")


# ──────────────────────────────────────────────────────────────────────
# Backend handlers
# ──────────────────────────────────────────────────────────────────────


async def _execute_builtin(
    tool: Tool, inputs: dict[str, Any], ctx: DispatchContext, timeout_ms: int
) -> BuiltinResult:
    handler_name = (tool.config or {}).get("handler")
    if not handler_name:
        return BuiltinResult(success=False, error="builtin tool missing config.handler")
    options = (tool.config or {}).get("options") or {}
    # Pass `auth_config` so builtins can read per-tool credentials (Tavily key,
    # Telegram bot token, etc.) without falling back to server env. Empty dict
    # is fine — builtins are responsible for deciding what to do when missing.
    builtin_ctx = BuiltinContext(
        workspace_id=ctx.workspace_id,
        agent_id=ctx.agent_id,
        run_id=ctx.run_id,
        user_id=ctx.user_id,
        options=options,
        auth=tool.auth_config or {},
    )
    return await run_builtin(handler_name, inputs, builtin_ctx, timeout_ms=timeout_ms)


async def _execute_http(
    tool: Tool, env: Mapping[str, Mapping[str, Any]], timeout_ms: int
) -> BuiltinResult:
    cfg = tool.config or {}
    method = (cfg.get("method") or "GET").upper()

    url = render(cfg.get("url"), env)
    if not url:
        return BuiltinResult(success=False, error="http tool missing url")

    _enforce_domain_guardrails(url, tool.guardrails or {})

    headers = {kv["key"]: render(kv["value"], env) for kv in (cfg.get("headers") or [])}
    params = {kv["key"]: render(kv["value"], env) for kv in (cfg.get("query_params") or [])}

    # Auth layer.
    auth_cfg = tool.auth_config or {}
    secret_refs = (auth_cfg.get("secret_refs") or {}) if isinstance(auth_cfg, dict) else {}
    secrets_env = env.get("secrets", {})
    if tool.auth_type == "bearer":
        token_key = secret_refs.get("token") or "token"
        token = secrets_env.get(token_key)
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif tool.auth_type == "api_key":
        header_name = auth_cfg.get("header_name") or "x-api-key"
        key_ref = secret_refs.get("api_key") or "api_key"
        key = secrets_env.get(key_ref)
        if key:
            headers[header_name] = key

    body_template = cfg.get("body_template")
    json_body: Any | None = None
    text_body: str | None = None
    if body_template is not None:
        rendered = render(body_template, env)
        if isinstance(rendered, str):
            text_body = rendered
        else:
            json_body = rendered

    try:
        async with httpx.AsyncClient(timeout=timeout_ms / 1000) as client:
            response = await client.request(
                method,
                url,
                headers=headers or None,
                params=params or None,
                json=json_body,
                content=text_body,
            )
        try:
            body: Any = response.json()
        except Exception:
            body = response.text
        return BuiltinResult(
            success=response.is_success,
            data={
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": body,
            },
            error=None if response.is_success else f"http {response.status_code}",
        )
    except httpx.HTTPError as exc:
        return BuiltinResult(success=False, error=f"http error: {exc}")


async def _execute_messaging(
    tool: Tool, inputs: dict[str, Any], _env: Mapping[str, Mapping[str, Any]]
) -> BuiltinResult:
    cfg = tool.config or {}
    provider = cfg.get("provider") or "slack"
    # Real send routes through the channels module. Here we queue an envelope
    # so the runtime layer can pick it up — keeps the executor non-blocking.
    return BuiltinResult(
        success=True,
        data={
            "queued": True,
            "provider": provider,
            "channel": inputs.get("channel") or inputs.get("chat_id"),
            "preview": str(inputs.get("message"))[:200],
        },
    )


async def _execute_agent_handoff(
    tool: Tool, inputs: dict[str, Any], ctx: DispatchContext
) -> BuiltinResult:
    cfg = tool.config or {}
    target = inputs.get("target_agent_id") or cfg.get("target_agent_id")
    if not target:
        return BuiltinResult(success=False, error="target_agent_id is required")
    # The agent runtime picks this up via runtime_events / agent_messages.
    return BuiltinResult(
        success=True,
        data={
            "queued": True,
            "from_agent_id": str(ctx.agent_id) if ctx.agent_id else None,
            "target_agent_id": str(target),
            "task": inputs.get("task"),
            "context": inputs.get("context"),
            "expected_output": inputs.get("expected_output"),
        },
    )


async def _execute_webhook(
    tool: Tool, env: Mapping[str, Mapping[str, Any]], timeout_ms: int
) -> BuiltinResult:
    cfg = tool.config or {}
    url = render(cfg.get("url"), env)
    if not url:
        return BuiltinResult(success=False, error="webhook tool missing url")
    _enforce_domain_guardrails(url, tool.guardrails or {})
    headers = {kv["key"]: render(kv["value"], env) for kv in (cfg.get("headers") or [])}
    body = render(cfg.get("body_template"), env)
    try:
        async with httpx.AsyncClient(timeout=timeout_ms / 1000) as client:
            response = await client.post(
                url,
                headers=headers or None,
                json=body if isinstance(body, dict | list) else None,
                content=body if isinstance(body, str) else None,
            )
        return BuiltinResult(
            success=response.is_success,
            data={"status_code": response.status_code},
            error=None if response.is_success else f"http {response.status_code}",
        )
    except httpx.HTTPError as exc:
        return BuiltinResult(success=False, error=f"webhook error: {exc}")


# ──────────────────────────────────────────────────────────────────────
# Top-level executor
# ──────────────────────────────────────────────────────────────────────


class ToolExecutor:
    def __init__(self, repository: ToolRepository) -> None:
        self.repository = repository

    # Hook for tests + the test-console: skip persistence by passing
    # ``record=False`` (returns a transient envelope only).
    async def execute(
        self,
        tool: Tool,
        inputs: dict[str, Any],
        ctx: DispatchContext,
        *,
        record: bool = True,
        dry_run: bool = False,
    ) -> ToolExecution | dict[str, Any]:
        execution: ToolExecution | None = None
        if record:
            execution = await self.repository.create_execution(
                workspace_id=ctx.workspace_id,
                run_id=ctx.run_id,
                run_node_id=ctx.run_node_id,
                tool_id=tool.id,
                tool_version=tool.version,
                agent_id=ctx.agent_id,
                tool_name=tool.slug,
                status="queued",
                input=inputs,
            )
            await self.repository.append_log(
                execution.id,
                level="info",
                message="execution.queued",
                metadata={"tool": tool.slug, "type": tool.type},
            )

        env = {
            "input": inputs,
            "secrets": ctx.secrets,
            "agent": {"id": str(ctx.agent_id) if ctx.agent_id else None},
            "workflow": {"run_id": str(ctx.run_id) if ctx.run_id else None},
            "workspace": {"id": str(ctx.workspace_id)},
        }

        # Approval gate.
        guardrails = tool.guardrails or {}
        if guardrails.get("requires_human_approval"):
            if execution is not None:
                await self.repository.update_execution(execution, status="pending_approval")
                await self.repository.create_approval(
                    execution_id=execution.id,
                    workspace_id=ctx.workspace_id,
                    requested_by_agent_id=ctx.agent_id,
                    prompt=guardrails.get("confirmation_message"),
                    status="pending",
                )
                await self.repository.append_log(
                    execution.id,
                    level="info",
                    message="execution.pending_approval",
                )
                return execution
            return {"success": False, "error": "pending_approval"}

        if dry_run:
            if execution is not None:
                await self.repository.update_execution(
                    execution,
                    status="success",
                    output={"dry_run": True, "resolved_config": render(tool.config or {}, env)},
                    completed_at=datetime.now(UTC),
                    duration_ms=0,
                )
            return {
                "success": True,
                "dry_run": True,
                "resolved_config": render(tool.config or {}, env),
            }

        policy = tool.execution_policy or {}
        timeout_ms = int(policy.get("timeout_ms") or 10_000)
        max_retries = int(policy.get("retry_count") or 0)
        backoff_ms = int(policy.get("retry_backoff_ms") or 500)

        if execution is not None:
            await self.repository.update_execution(execution, status="running")
            await self.repository.append_log(
                execution.id, level="info", message="execution.running"
            )

        started = time.perf_counter()
        last_result: BuiltinResult | None = None
        last_error: str | None = None
        attempts = 0

        for attempt in range(max_retries + 1):
            attempts = attempt + 1
            try:
                last_result = await self._dispatch(tool, inputs, env, ctx, timeout_ms)
                last_error = last_result.error
                if last_result.success:
                    break
            except GuardrailViolation as exc:
                last_result = BuiltinResult(success=False, error=str(exc))
                last_error = str(exc)
                # Guardrail violations don't retry.
                break
            except TimeoutError:
                last_result = BuiltinResult(success=False, error=f"timeout after {timeout_ms}ms")
                last_error = last_result.error
            except Exception as exc:  # defensive — never let executor raise
                log.exception("tool.execute.unhandled", tool_id=str(tool.id))
                last_result = BuiltinResult(success=False, error=f"unhandled: {exc}")
                last_error = last_result.error

            if attempt < max_retries:
                if execution is not None:
                    await self.repository.append_log(
                        execution.id,
                        level="warn",
                        message="execution.retry",
                        metadata={
                            "attempt": attempts,
                            "error": last_error,
                            "backoff_ms": backoff_ms,
                        },
                    )
                await asyncio.sleep(backoff_ms / 1000)

        duration_ms = int((time.perf_counter() - started) * 1000)
        success = bool(last_result and last_result.success)
        status = "success" if success else "failed"

        if last_result is not None and last_result.error == f"timeout after {timeout_ms}ms":
            status = "timeout"

        if execution is not None:
            await self.repository.update_execution(
                execution,
                status=status,
                output=(last_result.as_dict() if last_result else {}),
                error_message=None if success else last_error,
                duration_ms=duration_ms,
                retry_count=attempts - 1,
                completed_at=datetime.now(UTC),
            )
            await self.repository.append_log(
                execution.id,
                level="info" if success else "error",
                message=f"execution.{status}",
                metadata={"duration_ms": duration_ms, "retries": attempts - 1},
            )

            # Fallback chain.
            if not success and policy.get("fallback_tool_id"):
                fallback_id = policy["fallback_tool_id"]
                fallback = await self.repository.get(UUID(str(fallback_id)))
                if fallback is not None:
                    await self.repository.append_log(
                        execution.id,
                        level="info",
                        message="execution.fallback",
                        metadata={"fallback_tool_id": str(fallback.id)},
                    )
                    return await self.execute(fallback, inputs, ctx, record=record)

            return execution

        envelope: dict[str, Any] = last_result.as_dict() if last_result else {"success": False}
        envelope["duration_ms"] = duration_ms
        envelope["retries"] = attempts - 1
        return envelope

    # ── Per-type dispatch ────────────────────────────────────────────

    async def _dispatch(
        self,
        tool: Tool,
        inputs: dict[str, Any],
        env: Mapping[str, Mapping[str, Any]],
        ctx: DispatchContext,
        timeout_ms: int,
    ) -> BuiltinResult:
        type_ = tool.type
        if type_ == "builtin":
            return await _execute_builtin(tool, inputs, ctx, timeout_ms)
        if type_ == "http":
            return await _execute_http(tool, env, timeout_ms)
        if type_ == "messaging":
            return await _execute_messaging(tool, inputs, env)
        if type_ == "agent_handoff":
            return await _execute_agent_handoff(tool, inputs, ctx)
        if type_ == "webhook":
            return await _execute_webhook(tool, env, timeout_ms)
        if type_ == "mock":
            return BuiltinResult(success=True, data={"echo": inputs})
        return BuiltinResult(success=False, error=f"unsupported tool type: {type_!r}")


__all__ = ["DispatchContext", "GuardrailViolation", "ToolExecutor", "render"]


# Reuse the registry lookup at import time so an unregistered handler
# fails fast when its `Tool` row is created instead of at dispatch time.
def builtin_exists(name: str) -> bool:
    return get_builtin(name) is not None
