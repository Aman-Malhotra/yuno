from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, IdMixin


class AgentMessage(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "agent_messages"
    __table_args__ = (
        CheckConstraint(
            "direction IN ('inbound', 'outbound', 'internal')",
            name="ck_agent_messages_direction",
        ),
        CheckConstraint(
            "role IN ('system', 'user', 'assistant', 'tool', 'agent')",
            name="ck_agent_messages_role",
        ),
        CheckConstraint(
            "content_type IN ('text', 'json', 'markdown', 'image', 'file')",
            name="ck_agent_messages_content_type",
        ),
        Index("idx_agent_messages_workspace_id", "workspace_id"),
        Index("idx_agent_messages_run_id", "run_id"),
        Index("idx_agent_messages_conversation_id", "conversation_id"),
        Index("idx_agent_messages_from_agent_id", "from_agent_id"),
        Index("idx_agent_messages_to_agent_id", "to_agent_id"),
        Index("idx_agent_messages_created_at", "created_at"),
        Index("idx_agent_messages_metadata_gin", "metadata", postgresql_using="gin"),
    )

    workspace_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )

    run_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    run_node_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workflow_run_nodes.id", ondelete="SET NULL"),
        nullable=True,
    )

    conversation_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)

    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)

    from_agent_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    to_agent_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )

    from_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    channel_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    external_channel_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(
        String(16), nullable=False, default="text", server_default="text"
    )

    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )
