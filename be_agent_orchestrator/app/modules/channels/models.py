from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, IdMixin, SoftDeleteMixin, TimestampMixin


class ChannelConnection(Base, IdMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "channel_connections"
    __table_args__ = (
        CheckConstraint(
            "channel_type IN ('telegram', 'slack', 'whatsapp')",
            name="ck_channel_connections_channel_type",
        ),
        CheckConstraint(
            "status IN ('active', 'disabled', 'error')",
            name="ck_channel_connections_status",
        ),
        Index("idx_channel_connections_workspace_id", "workspace_id"),
        Index("idx_channel_connections_agent_id", "agent_id"),
        Index("idx_channel_connections_channel_type", "channel_type"),
    )

    workspace_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )

    channel_type: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")

    external_bot_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_workspace_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_channel_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    secret_refs: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_connected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_by: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )


class ChannelMessage(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "channel_messages"
    __table_args__ = (
        CheckConstraint(
            "direction IN ('inbound', 'outbound')",
            name="ck_channel_messages_direction",
        ),
        Index("idx_channel_messages_connection_id", "channel_connection_id"),
        Index("idx_channel_messages_external_chat_id", "external_chat_id"),
        Index("idx_channel_messages_created_at", "created_at"),
    )

    workspace_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel_connection_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("channel_connections.id", ondelete="CASCADE"),
        nullable=False,
    )

    agent_message_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("agent_messages.id", ondelete="SET NULL"),
        nullable=True,
    )

    channel_type: Mapped[str] = mapped_column(String(32), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)

    external_chat_id: Mapped[str] = mapped_column(String(255), nullable=False)
    external_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
