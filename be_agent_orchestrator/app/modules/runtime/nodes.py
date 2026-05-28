"""Per-node runners.

Each runner takes the compiled-graph node dict + a ``NodeContext`` (state +
service handles) and returns a ``NodeResult`` (the delta to merge into
state under the node id, plus token usage / tool id). The executor wraps
the runner call with persistence hooks for the node row + node-level
events; the agent runner additionally emits ``tool.called`` /
``tool.result`` events for each function call inside its tool-calling loop.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agents.models import Agent
from app.modules.agents.service import AgentService
from app.modules.llm.factory import LLMFactory
from app.modules.llm.schemas import (
    LLMMessage,
    LLMRequest,
    LLMResponse,
    LLMToolCall,
    LLMToolDescriptor,
    TokenUsage,
)
from app.modules.memory.service import MemoryService
from app.modules.messages.repository import AgentMessageRepository
from app.modules.runtime import memory_hooks
from app.modules.runtime.events import RunPersistence
from app.modules.runtime.state import RunState, render_template
from app.modules.tools.executor import DispatchContext, ToolExecutor
from app.modules.tools.models import Tool
from app.modules.tools.repository import ToolRepository

# Hard ceiling on tool-call hops inside a single agent turn. Most agents
# need 1–3; anything higher is usually a prompt bug producing infinite
# self-calls. Each agent can override via ``guardrails_config.max_tool_hops``.
DEFAULT_MAX_TOOL_HOPS = 5


@dataclass
class NodeContext:
    """Per-node execution context passed into every runner."""

    db: AsyncSession
    workspace_id: UUID
    run_id: UUID
    run_node_id: UUID
    state: RunState
    # Graph-level node id (e.g. ``"intake"``, ``"triage"``). Stamped on
    # every event the runner emits so the UI can filter events per step
    # (``run_node_id`` is the DB row id; this is the human-readable
    # handle the workflow author chose).
    graph_node_id: str = ""


@dataclass
class NodeResult:
    """What a runner reports back to the executor.

    ``output`` is what gets persisted on ``workflow_run_nodes.output`` *and*
    merged into state under the node id. ``tokens`` is rolled up into the
    run-level totals. ``agent_id`` / ``tool_id`` enrich the event stream.
    """

    output: dict[str, Any]
    tokens: TokenUsage = field(default_factory=TokenUsage)
    agent_id: UUID | None = None
    tool_id: UUID | None = None


class NodeRunnerError(Exception):
    """A runner reports a clean failure (bad config, missing agent, …).

    Distinct from raw exceptions so the executor can attribute the error
    to the node without surfacing a stack trace to the user.

    ``partial_output`` lets a runner ship whatever it managed to collect
    before failing — e.g. an agent that ran 3 tool calls and then hit the
    hop limit can attach the ``tool_call_log`` so the run detail still
    shows what happened. The executor merges this into
    ``workflow_run_nodes.output``.
    """

    def __init__(self, message: str, *, partial_output: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.partial_output: dict[str, Any] | None = partial_output


# ──────────────────────────────────────────────────────────────────────
# Trivial runners — no work, just pass state through
# ──────────────────────────────────────────────────────────────────────


async def run_passthrough(node: dict[str, Any], ctx: NodeContext) -> NodeResult:  # noqa: ARG001
    return NodeResult(output={})


# ──────────────────────────────────────────────────────────────────────
# Agent node — tool-calling loop
# ──────────────────────────────────────────────────────────────────────


async def run_agent(
    node: dict[str, Any],
    ctx: NodeContext,
    *,
    agent_service: AgentService,
    tool_executor: ToolExecutor,
    tool_repository: ToolRepository,
    persistence: RunPersistence,
    memory_service: MemoryService | None = None,
    message_repository: AgentMessageRepository | None = None,
    workflow_id: UUID | None = None,
) -> NodeResult:
    """Run one agent turn — may loop through several tool calls.

    Pipeline:
      1. Load the agent row, resolve its API key (BYOK → vault → env).
      2. Resolve every tool slug in ``skills_config.tools`` to a ``Tool`` row
         and a function descriptor for the LLM.
      3. Memory pre-hook (when channel-bound): fetch Layer-1 transcript
         + Layer-3 mem0 recall and prepend to the message list.
      4. Loop: call LLM → if response has tool_calls, execute each via
         ``ToolExecutor`` and append the results as ``tool`` messages → call
         LLM again. Stop when LLM returns content without tool_calls, or
         when we hit ``max_tool_hops``.
      5. Emit ``tool.called`` / ``tool.result`` events for every call so
         the runs UI's tool-count panel populates.
      6. Memory post-hook: persist the inbound + outbound turns and push
         them to mem0 for long-term extraction.
    """

    agent = await _load_agent(node, ctx)
    api_key = await agent_service.resolve_api_key(agent)
    if not api_key:
        raise NodeRunnerError(
            f"no API key resolvable for agent {agent.slug} (provider {agent.model_provider})"
        )

    tool_descriptors, tools_by_name = await _resolve_agent_tools(
        agent, tool_repository, workspace_id=ctx.workspace_id
    )

    provider = LLMFactory.create(
        agent.model_provider,
        {
            "api_key": api_key,
            "model": agent.model_name,
            "temperature": float(agent.temperature),
            "max_tokens": agent.max_tokens,
        },
    )

    current_user_message = _build_agent_input(node, ctx.state)

    # Memory pre-hook. Returns None when the run isn't channel-bound — in
    # which case we run without prior context, the existing behavior.
    mem_ctx = None
    history_prefix: list[LLMMessage] = []
    if memory_service is not None and message_repository is not None:
        mem_ctx = memory_hooks.derive(
            agent=agent,
            state=ctx.state,
            workspace_id=ctx.workspace_id,
            workflow_id=workflow_id,
        )
        if mem_ctx is not None:
            history_prefix = await memory_hooks.prepare(
                ctx=mem_ctx,
                current_user_message=current_user_message,
                message_repository=message_repository,
                memory_service=memory_service,
            )

    messages: list[LLMMessage] = [
        LLMMessage(role="system", content=agent.system_prompt),
        *history_prefix,
        LLMMessage(role="user", content=current_user_message),
    ]
    total_usage = TokenUsage()
    tool_call_log: list[dict[str, Any]] = []
    max_hops = int((agent.guardrails_config or {}).get("max_tool_hops", DEFAULT_MAX_TOOL_HOPS))

    for _ in range(max_hops + 1):
        response = await _complete(provider, agent, messages, tool_descriptors)
        total_usage = total_usage + response.usage

        if not response.tool_calls:
            content = response.message.content
            output: dict[str, Any] = {"tool_calls": tool_call_log}
            # If the agent replied with a JSON object (our seeded prompts ask
            # for exactly that), spread the parsed fields onto the output so
            # downstream conditional edges can read e.g. `state.router.intent`
            # directly. We deliberately do NOT also keep the raw `content`
            # string — that was producing duplicated, double-encoded data in
            # the state blob. Prose replies still get `content` (the
            # fallback branch below).
            parsed = _maybe_parse_json_object(content)
            if parsed is not None:
                for key, value in parsed.items():
                    if key != "tool_calls":  # reserved
                        output[key] = value
            else:
                output["content"] = content

            # Memory post-hook: write L1 rows + push to mem0. Skipped when
            # this run isn't channel-bound, or when the LLM returned no text
            # (purely a tool-routing turn with no user-facing reply yet).
            if (
                mem_ctx is not None
                and memory_service is not None
                and message_repository is not None
                and content
            ):
                await memory_hooks.persist(
                    ctx=mem_ctx,
                    inbound=current_user_message,
                    outbound=content,
                    run_id=ctx.run_id,
                    run_node_id=ctx.run_node_id,
                    message_repository=message_repository,
                    memory_service=memory_service,
                )

            return NodeResult(
                output=output,
                tokens=total_usage,
                agent_id=agent.id,
            )

        # Round-trip: the assistant turn that requested the tools has to be
        # part of the next request so the tool messages can reference its
        # call ids. Use content="" when the model gave us none.
        messages.append(
            LLMMessage(
                role="assistant",
                content=response.message.content or "",
                tool_calls=response.tool_calls,
            )
        )

        for call in response.tool_calls:
            tool_msg = await _execute_tool_call(
                call=call,
                tools_by_name=tools_by_name,
                tool_executor=tool_executor,
                ctx=ctx,
                agent=agent,
                persistence=persistence,
                tool_call_log=tool_call_log,
            )
            messages.append(tool_msg)

    # Ran out of hops. Ship the partial tool_call_log so the run detail
    # still tells the operator what the agent *did* manage before being
    # cut off — without this, the failed node row has output={} and the
    # post-mortem is just the error string.
    raise NodeRunnerError(
        f"agent {agent.slug} exceeded max_tool_hops={max_hops} — likely an infinite tool loop",
        partial_output={
            "tool_calls": tool_call_log,
            "hops_used": max_hops + 1,
            "last_assistant_content": response.message.content,
        },
    )


# ──────────────────────────────────────────────────────────────────────
# Tool node — fire one ToolExecutor invocation
# ──────────────────────────────────────────────────────────────────────


async def run_tool(
    node: dict[str, Any],
    ctx: NodeContext,
    *,
    tool_executor: ToolExecutor,
) -> NodeResult:
    tool_id_raw = node.get("tool_id")
    if not tool_id_raw:
        raise NodeRunnerError(f"tool node {node['id']!r} has no tool_id")
    try:
        tool_id = UUID(str(tool_id_raw))
    except ValueError as err:
        raise NodeRunnerError(f"tool node {node['id']!r}: invalid tool_id {tool_id_raw!r}") from err

    tool = (
        await ctx.db.execute(select(Tool).where(Tool.id == tool_id, Tool.deleted_at.is_(None)))
    ).scalar_one_or_none()
    if tool is None:
        raise NodeRunnerError(f"tool {tool_id} not found")

    inputs = _build_tool_input(node, ctx.state)
    dispatch_ctx = DispatchContext(
        workspace_id=ctx.workspace_id,
        run_id=ctx.run_id,
        run_node_id=ctx.run_node_id,
    )
    execution = await tool_executor.execute(tool, inputs, dispatch_ctx)

    output: dict[str, Any] = (
        execution.output if hasattr(execution, "output") and execution.output is not None else {}
    )
    success = getattr(execution, "status", None) == "success"
    if not success:
        raise NodeRunnerError(
            f"tool {tool.slug} failed: {getattr(execution, 'error_message', None) or 'unknown'}"
        )

    return NodeResult(output=output, tool_id=tool.id)


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────


async def _load_agent(node: dict[str, Any], ctx: NodeContext) -> Agent:
    raw = node.get("agent_id")
    if not raw:
        raise NodeRunnerError(f"agent node {node['id']!r} has no agent_id")
    try:
        agent_id = UUID(str(raw))
    except ValueError as err:
        raise NodeRunnerError(f"agent node {node['id']!r}: invalid agent_id {raw!r}") from err

    agent = (
        await ctx.db.execute(select(Agent).where(Agent.id == agent_id, Agent.deleted_at.is_(None)))
    ).scalar_one_or_none()
    if agent is None:
        raise NodeRunnerError(f"agent {agent_id} not found")
    return agent


async def _resolve_agent_tools(
    agent: Agent,
    tool_repository: ToolRepository,
    *,
    workspace_id: UUID,
) -> tuple[list[LLMToolDescriptor], dict[str, Tool]]:
    """Read ``skills_config.tools`` and resolve each slug to a (descriptor, Tool).

    Unknown slugs are dropped with a logged warning — we'd rather run the
    agent without a missing tool than crash the whole workflow.
    """

    entries = (agent.skills_config or {}).get("tools", []) or []
    descriptors: list[LLMToolDescriptor] = []
    tools_by_name: dict[str, Tool] = {}
    for entry in entries:
        slug = entry.get("name") if isinstance(entry, dict) else None
        if not slug:
            continue
        tool = await tool_repository.get_by_slug(workspace_id, slug)
        if tool is None:
            continue
        # Function names allow [a-zA-Z0-9_-] so slugs pass through as-is.
        descriptor = LLMToolDescriptor(
            name=tool.slug,
            description=tool.description or "",
            parameters_schema=tool.input_schema or {"type": "object", "properties": {}},
        )
        descriptors.append(descriptor)
        tools_by_name[descriptor.name] = tool
    return descriptors, tools_by_name


async def _complete(
    provider: Any,
    agent: Agent,
    messages: list[LLMMessage],
    tools: list[LLMToolDescriptor],
) -> LLMResponse:
    request = LLMRequest(
        model=agent.model_name,
        temperature=float(agent.temperature),
        max_tokens=agent.max_tokens,
        messages=messages,
        tools=tools,
    )
    return await provider.complete(request)  # type: ignore[no-any-return]


async def _execute_tool_call(
    *,
    call: LLMToolCall,
    tools_by_name: dict[str, Tool],
    tool_executor: ToolExecutor,
    ctx: NodeContext,
    agent: Agent,
    persistence: RunPersistence,
    tool_call_log: list[dict[str, Any]],
) -> LLMMessage:
    """Execute one tool call requested by the agent.

    Always returns a ``tool``-role message — even on failure, so the LLM
    can read the error and decide what to do next. Emits one ``tool.called``
    event and one ``tool.result`` event per call for the live timeline.
    """

    tool = tools_by_name.get(call.name)
    if tool is None:
        result_payload: dict[str, Any] = {
            "success": False,
            "error": f"unknown tool: {call.name}",
        }
        await persistence.emit(
            "tool.called",
            node_id=ctx.graph_node_id or None,
            run_node_id=ctx.run_node_id,
            agent_id=agent.id,
            message=call.name,
            payload={"arguments": call.arguments, "error": "unknown_tool"},
        )
        tool_call_log.append(
            {"name": call.name, "arguments": call.arguments, "result": result_payload}
        )
        return LLMMessage(
            role="tool",
            content=json.dumps(result_payload),
            tool_call_id=call.id,
            name=call.name,
        )

    await persistence.emit(
        "tool.called",
        node_id=ctx.graph_node_id or None,
        run_node_id=ctx.run_node_id,
        agent_id=agent.id,
        tool_id=tool.id,
        message=tool.slug,
        payload={"arguments": call.arguments},
    )

    dispatch_ctx = DispatchContext(
        workspace_id=ctx.workspace_id,
        agent_id=agent.id,
        run_id=ctx.run_id,
        run_node_id=ctx.run_node_id,
    )
    execution = await tool_executor.execute(tool, call.arguments, dispatch_ctx)

    # ``execution.output`` already carries ``BuiltinResult.as_dict()`` shape:
    # ``{"success": bool, "data": {...}, "error": str|None}``. Don't re-wrap
    # it — that's what created the nested ``data.data.ticket`` blobs in the
    # state. Pull the *inner* data + error straight out.
    if hasattr(execution, "output"):
        success = getattr(execution, "status", None) == "success"
        envelope: dict[str, Any] = execution.output or {}
        error: str | None = getattr(execution, "error_message", None) or envelope.get("error")
    else:
        # ``record=False`` path — same envelope shape, different source.
        envelope = execution
        success = bool(envelope.get("success"))
        error = envelope.get("error")

    inner_data = envelope.get("data") if isinstance(envelope.get("data"), dict | list) else envelope
    result_payload = {"success": success, "data": inner_data, "error": error}
    tool_call_log.append({"name": call.name, "arguments": call.arguments, "result": result_payload})

    await persistence.emit(
        "tool.result",
        node_id=ctx.graph_node_id or None,
        run_node_id=ctx.run_node_id,
        agent_id=agent.id,
        tool_id=tool.id,
        message=tool.slug,
        payload=result_payload,
    )

    return LLMMessage(
        role="tool",
        content=json.dumps(result_payload, default=str),
        tool_call_id=call.id,
        name=call.name,
    )


def _maybe_parse_json_object(content: str | None) -> dict[str, Any] | None:
    """Best-effort: return the parsed dict if `content` is a JSON object.

    Returns None on anything else (None input, prose, JSON array/scalar,
    parse failure). Common LLM quirks tolerated:
      * surrounding markdown fences (```json ... ```)
      * leading/trailing whitespace
    """

    if not content:
        return None
    text = content.strip()
    if text.startswith("```"):
        # Strip ```json (or ```) and the trailing ``` fence.
        text = text.removeprefix("```json").removeprefix("```").strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    if not (text.startswith("{") and text.endswith("}")):
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _build_agent_input(node: dict[str, Any], state: RunState) -> str:
    """Render the user message we send to the LLM.

    Precedence:
    1. ``input_template`` on the node (e.g. ``{{message.text}}``) — rendered.
    2. ``state.message`` if present — covers the common channel-trigger case
       where the webhook body looks like ``{"message": "..."}``.
    3. Whole state JSON — fallback so the agent always sees *something*.
    """

    template = node.get("input_template")
    if template:
        return render_template(str(template), state)
    message = state.get_path("message")
    if isinstance(message, str) and message:
        return message
    return json.dumps(state.as_dict(), default=str, indent=2)


def _build_tool_input(node: dict[str, Any], state: RunState) -> dict[str, Any]:
    """Tools accept ``inputs`` as a dict. Pull from ``node.input`` or fall
    back to the whole state. Templates inside dict values are rendered."""

    raw = node.get("input")
    if isinstance(raw, dict) and raw:
        rendered = _render_dict(raw, state)
        return rendered if isinstance(rendered, dict) else state.as_dict()
    return state.as_dict()


def _render_dict(value: Any, state: RunState) -> Any:
    if isinstance(value, str):
        return render_template(value, state)
    if isinstance(value, list):
        return [_render_dict(v, state) for v in value]
    if isinstance(value, dict):
        return {k: _render_dict(v, state) for k, v in value.items()}
    return value
