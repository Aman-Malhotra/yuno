"""Per-agent memory hooks — Layer 1 (conversation history) + Layer 3 (mem0).

Why a separate module
---------------------
``run_agent`` is already long. Memory wiring is a strict pre/post around
the LLM tool-loop, with its own error model (a failure here must NEVER
crash the run — the agent stays useful without memory). Pulling it out
keeps the runner readable and lets us test the hooks in isolation.

Contract
--------
- ``prepare`` returns a list of LLM messages to PREPEND to the system
  prompt + current user message. May be empty (no history / mem0 off).
- ``persist`` writes the inbound + outbound rows AND, if long-term is
  enabled, fires-and-forgets a mem0 ``add`` so the next turn can recall
  the extracted facts.

Both functions degrade gracefully — missing state fields, mem0 outage,
or a fresh chat with zero prior turns all return empty / no-ops rather
than raising.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

import structlog

from app.core.config import settings
from app.modules.agents.models import Agent
from app.modules.llm.schemas import LLMMessage
from app.modules.memory.schemas import MemoryEntry
from app.modules.memory.service import MemoryService
from app.modules.messages.repository import (
    AgentMessageRepository,
    conversation_id_for,
)
from app.modules.runtime.state import RunState

log = structlog.get_logger("runtime.memory")


@dataclass
class MemoryContext:
    """All the keys we derive once and reuse across prepare/persist.

    Returns ``None`` from ``derive`` when the run isn't channel-bound
    (manual /test runs, internal worker triggers) — memory hooks no-op
    in that case so we don't pollute mem0 with synthetic test turns.
    """

    workspace_id: UUID
    agent_id: UUID
    conversation_id: UUID
    channel_type: str
    external_channel_id: str
    memory_user_id: str
    username: str | None
    workflow_id: UUID | None
    history_turns: int
    recall_k: int
    enable_long_term: bool


def derive(
    *,
    agent: Agent,
    state: RunState,
    workspace_id: UUID,
    workflow_id: UUID | None,
) -> MemoryContext | None:
    """Pull memory params from the agent config + the current run state."""

    channel = state.get_path("channel")
    chat_id = state.get_path("chat_id")
    if not channel or chat_id is None:
        return None

    mem_cfg = agent.memory_config or {}
    history_turns = int(mem_cfg.get("history_turns", settings.memory_default_history_turns))
    recall_k = int(mem_cfg.get("recall_k", settings.memory_default_recall_k))
    enable_long_term = bool(mem_cfg.get("enable_long_term", True))

    # Prefer the stable platform user id; fall back to chat_id when the
    # channel does not split them (group chats, anonymous webhooks).
    user_id_raw = (
        state.get_path("telegram_user_id")
        or state.get_path("user.id")
        or state.get_path("user_id")
        or chat_id
    )

    external_channel_id = str(chat_id)
    return MemoryContext(
        workspace_id=workspace_id,
        agent_id=agent.id,
        conversation_id=conversation_id_for(
            channel_type=str(channel),
            external_channel_id=external_channel_id,
            agent_id=agent.id,
        ),
        channel_type=str(channel),
        external_channel_id=external_channel_id,
        memory_user_id=str(user_id_raw),
        username=_str_or_none(state.get_path("username") or state.get_path("user.username")),
        workflow_id=workflow_id,
        history_turns=history_turns,
        recall_k=recall_k,
        enable_long_term=enable_long_term,
    )


# ──────────────────────────────────────────────────────────────────────
# Prepare — fetch L1 + L3, build the message prefix
# ──────────────────────────────────────────────────────────────────────


async def prepare(
    *,
    ctx: MemoryContext,
    current_user_message: str,
    message_repository: AgentMessageRepository,
    memory_service: MemoryService,
) -> list[LLMMessage]:
    """Build the prior-turns prefix the LLM sees before the new user message.

    Order in the returned list:
      1. (optional) one ``system`` message listing relevant long-term
         memories — only if mem0 returned any.
      2. The last ``history_turns`` inbound/outbound rows as user/assistant
         turns in chronological order.
    """

    prefix: list[LLMMessage] = []

    # Layer 3 — semantic recall scoped to user_id. Skip if disabled.
    if ctx.enable_long_term and ctx.recall_k > 0:
        memories = await memory_service.search(
            current_user_message,
            user_id=ctx.memory_user_id,
            limit=ctx.recall_k,
        )
        recalled = _format_memories(memories)
        if recalled:
            prefix.append(LLMMessage(role="system", content=recalled))

    # Layer 1 — exact transcript replay.
    if ctx.history_turns > 0:
        history = await message_repository.list_for_conversation(
            ctx.conversation_id,
            limit=ctx.history_turns,
        )
        for row in history:
            role = "assistant" if row.direction == "outbound" else "user"
            prefix.append(LLMMessage(role=role, content=row.content))

    return prefix


def _format_memories(entries: list[MemoryEntry]) -> str:
    """Render the recall list as a tight bullet block.

    Includes only the memory text + the user's friendly handle so the LLM
    knows who the speaker is, without leaking internal ids.
    """

    if not entries:
        return ""
    lines = ["Relevant things you remember about this user:"]
    for e in entries:
        username = (e.metadata or {}).get("username")
        prefix = f"@{username}" if username else "user"
        lines.append(f"- ({prefix}) {e.memory}")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────
# Persist — write L1 rows + push to mem0
# ──────────────────────────────────────────────────────────────────────


async def persist(
    *,
    ctx: MemoryContext,
    inbound: str,
    outbound: str,
    run_id: UUID,
    run_node_id: UUID,
    message_repository: AgentMessageRepository,
    memory_service: MemoryService,
) -> None:
    """Write the user + assistant turns; fire mem0.add for the same pair.

    mem0.add runs its own Groq-powered extractor and may produce 0..N
    memory rows. We don't await its result beyond completion — failures
    are logged but never raised.
    """

    # Layer 1 only. mem0 (Layer 3) is deliberately NOT fired per agent —
    # a Telegram message that travels through router → composer would
    # produce 2 mem0 extractions of the same user utterance otherwise.
    # The executor calls ``persist_to_memory_once`` at run end instead.
    try:
        await message_repository.create_inbound(
            workspace_id=ctx.workspace_id,
            conversation_id=ctx.conversation_id,
            content=inbound,
            run_id=run_id,
            run_node_id=run_node_id,
            to_agent_id=ctx.agent_id,
            channel_type=ctx.channel_type,
            external_channel_id=ctx.external_channel_id,
            external_user_id=ctx.memory_user_id,
            metadata={"username": ctx.username} if ctx.username else {},
        )
        await message_repository.create_outbound(
            workspace_id=ctx.workspace_id,
            conversation_id=ctx.conversation_id,
            content=outbound,
            run_id=run_id,
            run_node_id=run_node_id,
            from_agent_id=ctx.agent_id,
            channel_type=ctx.channel_type,
            external_channel_id=ctx.external_channel_id,
            metadata={"username": ctx.username} if ctx.username else {},
        )
    except Exception as err:  # noqa: BLE001 — never crash the run on history write
        log.exception(
            "memory.l1.persist.failed",
            conversation_id=str(ctx.conversation_id),
            agent_id=str(ctx.agent_id),
            channel_type=ctx.channel_type,
            external_channel_id=ctx.external_channel_id,
            error_type=type(err).__name__,
            error=str(err),
        )


async def persist_to_memory_once(
    *,
    state: RunState,
    workspace_id: UUID,
    workflow_id: UUID | None,
    run_id: UUID,
    message_repository: AgentMessageRepository,
    memory_service: MemoryService,
) -> None:
    """Single mem0 extraction per workflow run.

    Reads the L1 rows for this run, builds ONE user/assistant pair from
    the first inbound and last outbound message, and pushes it to mem0.
    This is what turns the workflow's collaboration into a single
    "user said X → assistant replied Y" memory event, regardless of how
    many agents participated.

    No-ops cleanly when:
    - The run isn't channel-bound (no chat_id / channel in state)
    - Long-term memory is disabled across the board for this workflow
    - No outbound message was produced (the agents never replied)
    """

    channel = state.get_path("channel")
    chat_id = state.get_path("chat_id")
    if not channel or chat_id is None:
        return

    user_id_raw = (
        state.get_path("telegram_user_id")
        or state.get_path("user.id")
        or state.get_path("user_id")
        or chat_id
    )
    username = _str_or_none(state.get_path("username") or state.get_path("user.username"))
    external_channel_id = str(chat_id)

    try:
        rows = await message_repository.list_for_run(run_id)
    except Exception as err:  # noqa: BLE001
        log.exception(
            "memory.run.fetch.failed",
            run_id=str(run_id),
            error_type=type(err).__name__,
            error=str(err),
        )
        return

    inbound_row = next((r for r in rows if r.direction == "inbound"), None)
    outbound_row = next((r for r in reversed(rows) if r.direction == "outbound"), None)
    if inbound_row is None or outbound_row is None:
        return

    await memory_service.add(
        [
            {"role": "user", "content": inbound_row.content},
            {"role": "assistant", "content": outbound_row.content},
        ],
        user_id=str(user_id_raw),
        metadata={
            "username": username,
            "chat_id": external_channel_id,
            "channel": str(channel),
            "workflow_id": str(workflow_id) if workflow_id else None,
            "run_id": str(run_id),
        },
    )


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
