"""AgentMessage repository — Layer-1 conversation history.

This is the per-conversation transcript store. The runtime writes one
row per inbound user message and one per outbound assistant reply; the
agent node replays the last N rows on the next turn so the LLM sees the
full thread.

Keying convention
-----------------
``conversation_id`` is a deterministic UUID v5 derived from
``(channel_type, external_channel_id, agent_id)``. Same chat + same
agent => same id, no extra table needed. Encoding ``agent_id`` keeps
parallel agents in the same chat in separate threads (so a router and a
chart-generator don't see each other's histories).
"""

from __future__ import annotations

from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.messages.models import AgentMessage

# Stable namespace UUID for v5 derivation. Generated once; never change.
_CONVERSATION_NAMESPACE = UUID("c0a4d2f8-4d1b-4a5e-9b2f-2c4f6d8a1e90")


def conversation_id_for(
    *,
    channel_type: str,
    external_channel_id: str,
    agent_id: UUID,
) -> UUID:
    """Deterministic conversation id — same inputs always yield the same UUID."""

    return uuid5(_CONVERSATION_NAMESPACE, f"{channel_type}:{external_channel_id}:{agent_id}")


class AgentMessageRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_inbound(
        self,
        *,
        workspace_id: UUID,
        conversation_id: UUID,
        content: str,
        run_id: UUID | None = None,
        run_node_id: UUID | None = None,
        to_agent_id: UUID | None = None,
        channel_type: str | None = None,
        external_channel_id: str | None = None,
        external_user_id: str | None = None,
        external_message_id: str | None = None,
        metadata: dict | None = None,
    ) -> AgentMessage:
        """Persist a user/inbound turn before the LLM sees it."""

        msg = AgentMessage(
            workspace_id=workspace_id,
            run_id=run_id,
            run_node_id=run_node_id,
            conversation_id=conversation_id,
            direction="inbound",
            role="user",
            to_agent_id=to_agent_id,
            channel_type=channel_type,
            external_channel_id=external_channel_id,
            external_user_id=external_user_id,
            external_message_id=external_message_id,
            content=content,
            content_type="text",
            metadata_=metadata or {},
        )
        self.db.add(msg)
        await self.db.commit()
        await self.db.refresh(msg)
        return msg

    async def create_outbound(
        self,
        *,
        workspace_id: UUID,
        conversation_id: UUID,
        content: str,
        run_id: UUID | None = None,
        run_node_id: UUID | None = None,
        from_agent_id: UUID | None = None,
        channel_type: str | None = None,
        external_channel_id: str | None = None,
        metadata: dict | None = None,
    ) -> AgentMessage:
        """Persist the assistant turn after the LLM produces its final reply."""

        msg = AgentMessage(
            workspace_id=workspace_id,
            run_id=run_id,
            run_node_id=run_node_id,
            conversation_id=conversation_id,
            direction="outbound",
            role="assistant",
            from_agent_id=from_agent_id,
            channel_type=channel_type,
            external_channel_id=external_channel_id,
            content=content,
            content_type="text",
            metadata_=metadata or {},
        )
        self.db.add(msg)
        await self.db.commit()
        await self.db.refresh(msg)
        return msg

    async def list_for_run(self, run_id: UUID) -> list[AgentMessage]:
        """All messages tied to a single workflow run, chronological.

        Used by the once-per-run memory hook in the executor: it picks
        the first inbound + last outbound to build a single mem0 turn.
        """

        stmt = (
            select(AgentMessage)
            .where(AgentMessage.run_id == run_id)
            .order_by(AgentMessage.created_at.asc())
        )
        return list((await self.db.execute(stmt)).scalars())

    async def list_for_conversation(
        self,
        conversation_id: UUID,
        *,
        limit: int,
    ) -> list[AgentMessage]:
        """Return the most recent ``limit`` rows, oldest-first.

        We pull DESC + LIMIT (so we get the latest N, not the first N
        ever) then reverse in-process so the LLM receives chronological
        order. ``limit=0`` short-circuits.
        """

        if limit <= 0:
            return []

        stmt = (
            select(AgentMessage)
            .where(AgentMessage.conversation_id == conversation_id)
            .order_by(AgentMessage.created_at.desc())
            .limit(limit)
        )
        rows = list((await self.db.execute(stmt)).scalars())
        rows.reverse()
        return rows
