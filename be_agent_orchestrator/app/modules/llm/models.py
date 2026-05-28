from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base, CreatedAtMixin, IdMixin, TimestampMixin


class LLMProviderConfig(Base, IdMixin, TimestampMixin):
    __tablename__ = "llm_provider_configs"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "provider",
            "display_name",
            name="uq_llm_provider_configs_ws_provider_name",
        ),
        CheckConstraint(
            "status IN ('active', 'disabled')",
            name="ck_llm_provider_configs_status",
        ),
        Index("idx_llm_provider_configs_workspace_id", "workspace_id"),
        Index("idx_llm_provider_configs_provider", "provider"),
    )

    workspace_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )

    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")

    api_key_secret_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_model: Mapped[str | None] = mapped_column(String(120), nullable=True)

    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    created_by: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )


class LLMModelCatalog(Base, IdMixin, TimestampMixin):
    __tablename__ = "llm_model_catalog"
    __table_args__ = (
        UniqueConstraint("provider", "model_name", name="uq_llm_model_catalog_provider_model"),
    )

    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)

    supports_tools: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    supports_streaming: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    supports_json_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    supports_vision: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    input_token_cost_usd: Mapped[float | None] = mapped_column(Numeric(12, 8), nullable=True)
    output_token_cost_usd: Mapped[float | None] = mapped_column(Numeric(12, 8), nullable=True)

    context_window_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )


class LLMCall(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "llm_calls"
    __table_args__ = (
        CheckConstraint(
            "request_type IN ('chat', 'completion', 'embedding', 'rerank')",
            name="ck_llm_calls_request_type",
        ),
        CheckConstraint(
            "status IN ('running', 'completed', 'failed', 'cancelled')",
            name="ck_llm_calls_status",
        ),
        Index("idx_llm_calls_workspace_id", "workspace_id"),
        Index("idx_llm_calls_run_id", "run_id"),
        Index("idx_llm_calls_agent_id", "agent_id"),
        Index("idx_llm_calls_provider_model", "provider", "model_name"),
        Index("idx_llm_calls_created_at", "created_at"),
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

    agent_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )

    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)

    request_type: Mapped[str] = mapped_column(String(32), nullable=False, default="chat")

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")

    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    input_cost_usd: Mapped[float] = mapped_column(
        Numeric(12, 8), nullable=False, default=0, server_default="0"
    )
    output_cost_usd: Mapped[float] = mapped_column(
        Numeric(12, 8), nullable=False, default=0, server_default="0"
    )
    total_cost_usd: Mapped[float] = mapped_column(
        Numeric(12, 8), nullable=False, default=0, server_default="0"
    )

    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    request_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    response_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkspaceLLMCredential(Base, IdMixin, TimestampMixin):
    """Workspace-scoped LLM provider credential.

    One row per (workspace, provider). Acts as the default key for every
    agent in the workspace whose own ``provider_credentials.api_key`` is
    empty. Same JSONB shape as ``UserLLMCredential.credentials``:
    ``{"api_key": "...", "base_url": "...", "organization": "..."}``.

    Resolution chain (at run time, in AgentService.resolve_api_key):
        agent.provider_credentials.api_key → this row → fail.
    No env / global fallback by design.
    """

    __tablename__ = "workspace_llm_credentials"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "provider", name="uq_workspace_llm_creds_workspace_provider"
        ),
        Index("idx_workspace_llm_creds_workspace_id", "workspace_id"),
    )

    workspace_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    credentials: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    created_by: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )


class UserLLMCredential(Base, IdMixin, TimestampMixin):
    """Per-user LLM provider credential vault row.

    One row per (user, provider). Used by the agent runtime to resolve an
    API key when an agent doesn't carry its own BYOK creds. UNIQUE constraint
    on (user_id, provider) → at most one credential per provider per user.

    Distinct from ``LLMProviderConfig`` which is workspace-scoped + targets
    a secrets-manager indirection layer; this table holds the user's own
    keys for their personal use across all workspaces.
    """

    __tablename__ = "user_llm_credentials"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_user_llm_creds_user_provider"),
        Index("idx_user_llm_creds_user_id", "user_id"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    credentials: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
