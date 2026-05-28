"""Builtin tool registry.

Each builtin is a callable that takes:
- ``inputs``: validated against the tool's ``input_schema``
- ``context``: ``BuiltinContext`` carrying agent/run/workspace ids and helpers

…and returns a ``BuiltinResult`` ``{"success", "data", "error"}``.

Adding a new builtin is a single-file change: implement the handler, decorate
with ``@register("name", description=..., input_schema=...)``, done. The tool
executor looks the handler up by ``config.handler``.

Handler implementations live in sibling modules and are imported here at the
bottom for side-effect registration:

* ``demo``     — mock CRM / refund / approval helpers backing the
                 Support Triage workflow.
* ``external`` — real network-hitting tools (Tavily web search, Telegram
                 ``sendMessage``).

The only handler in this file is ``ask_agent`` because it needs the
``BuiltinContext`` to stamp the originating agent on the envelope.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

# ──────────────────────────────────────────────────────────────────────
# Types
# ──────────────────────────────────────────────────────────────────────


@dataclass
class BuiltinContext:
    """Runtime context handed to a builtin handler.

    ``auth`` is the tool row's ``auth_config`` JSONB — the per-tool BYOK
    slot. Builtins should always prefer credentials from here over
    server-level env vars so each tool row can carry its own key
    (parallel to per-agent ``provider_credentials`` for LLMs).
    """

    workspace_id: UUID | None
    agent_id: UUID | None = None
    run_id: UUID | None = None
    user_id: UUID | None = None
    options: dict[str, Any] = field(default_factory=dict)
    auth: dict[str, Any] = field(default_factory=dict)


@dataclass
class BuiltinResult:
    success: bool
    data: Any = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"success": self.success}
        if self.data is not None:
            out["data"] = self.data
        if self.error is not None:
            out["error"] = self.error
        return out


Handler = Callable[[dict[str, Any], BuiltinContext], Awaitable[BuiltinResult]]


_DEFAULT_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean"},
        "data": {"type": "object"},
        "error": {"type": "string"},
    },
}


@dataclass
class BuiltinSpec:
    name: str
    description: str
    handler: Handler
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] = field(default_factory=lambda: dict(_DEFAULT_OUTPUT_SCHEMA))
    category: str = "general"


_REGISTRY: dict[str, BuiltinSpec] = {}


def register(
    name: str,
    *,
    description: str,
    input_schema: dict[str, Any],
    output_schema: dict[str, Any] | None = None,
    category: str = "general",
) -> Callable[[Handler], Handler]:
    def _decorator(handler: Handler) -> Handler:
        if name in _REGISTRY:
            raise RuntimeError(f"Duplicate builtin tool: {name!r}")
        _REGISTRY[name] = BuiltinSpec(
            name=name,
            description=description,
            handler=handler,
            input_schema=input_schema,
            output_schema=output_schema or dict(_DEFAULT_OUTPUT_SCHEMA),
            category=category,
        )
        return handler

    return _decorator


def get_builtin(name: str) -> BuiltinSpec | None:
    return _REGISTRY.get(name)


def list_builtins() -> list[BuiltinSpec]:
    return list(_REGISTRY.values())


# ──────────────────────────────────────────────────────────────────────
# ask_agent — kept here because the handler needs `BuiltinContext` to
# record the originating agent on the envelope.
# ──────────────────────────────────────────────────────────────────────


@register(
    "ask_agent",
    description=(
        "Delegate a sub-task to another agent and wait for its reply. Use when "
        "the target agent is better suited to the task (e.g. a Research agent "
        "for fact-finding, a Summarizer agent for compression)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "target_agent_id": {"type": "string", "description": "UUID of the agent to call."},
            "task": {"type": "string", "description": "The work to delegate."},
            "context": {"type": "string", "description": "Extra context the agent needs."},
            "expected_output": {"type": "string"},
        },
        "required": ["target_agent_id", "task"],
    },
    category="orchestration",
)
async def _ask_agent(inputs: dict[str, Any], ctx: BuiltinContext) -> BuiltinResult:
    # Currently a queued-envelope stub — the inter-agent dispatcher will pick
    # this up once the agent_messages persistence path lands. Until then it's
    # still useful: agents can declare the intent to hand off, which shows up
    # in the runs UI tool-call list.
    message_id = str(uuid4())
    return BuiltinResult(
        success=True,
        data={
            "message_id": message_id,
            "status": "queued",
            "from_agent_id": str(ctx.agent_id) if ctx.agent_id else None,
            "target_agent_id": inputs.get("target_agent_id"),
            "task": inputs.get("task"),
        },
    )


# ──────────────────────────────────────────────────────────────────────
# Dispatcher used by the tool executor
# ──────────────────────────────────────────────────────────────────────


async def run_builtin(
    handler_name: str,
    inputs: dict[str, Any],
    ctx: BuiltinContext,
    *,
    timeout_ms: int | None = None,
) -> BuiltinResult:
    spec = get_builtin(handler_name)
    if spec is None:
        return BuiltinResult(success=False, error=f"unknown builtin: {handler_name!r}")
    coro = spec.handler(inputs, ctx)
    if timeout_ms is None:
        return await coro
    try:
        return await asyncio.wait_for(coro, timeout=timeout_ms / 1000)
    except TimeoutError:
        return BuiltinResult(success=False, error=f"timeout after {timeout_ms}ms")


__all__ = [
    "BuiltinContext",
    "BuiltinResult",
    "BuiltinSpec",
    "get_builtin",
    "list_builtins",
    "register",
    "run_builtin",
]


# Side-effect imports: register handlers in sibling modules.
# Kept at the bottom so the public API above is in scope when those modules
# run ``register(...)`` at import time.
from app.modules.tools.builtins import demo as _demo  # noqa: E402,F401
from app.modules.tools.builtins import external as _external  # noqa: E402,F401
