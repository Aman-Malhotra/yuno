from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
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

from app.db.base import Base, CreatedAtMixin, IdMixin, SoftDeleteMixin, TimestampMixin

# ──────────────────────────────────────────────────────────────────────
# Tool — registry entry (one row per tool definition, workspace-scoped)
# ──────────────────────────────────────────────────────────────────────


class Tool(Base, IdMixin, TimestampMixin, SoftDeleteMixin):
    """A callable an agent can invoke during a run.

    Tool *type* determines the executor used at dispatch time. The five
    types we ship are:

    - ``builtin``       — registered handler in ``app.modules.tools.builtins``
    - ``http``          — REST API call, configured via ``config.http``
    - ``messaging``     — Slack / Telegram outbound, via ``config.messaging``
    - ``agent_handoff`` — calls another agent, treated as a tool message
    - ``webhook``       — fire-and-forget POST to an external URL

    The shape stored on the row is intentionally generic JSONB; the
    per-type validator lives next to its executor (not on the model) so
    new tool types can ship without a schema migration.
    """

    __tablename__ = "tools"
    __table_args__ = (
        UniqueConstraint("workspace_id", "slug", name="uq_tools_workspace_slug"),
        CheckConstraint(
            "type IN ('builtin', 'http', 'messaging', 'agent_handoff', 'webhook', "
            "'python', 'mock')",
            name="ck_tools_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'active', 'disabled', 'archived')",
            name="ck_tools_status",
        ),
        CheckConstraint(
            "auth_type IN ('none', 'bearer', 'api_key', 'basic', 'custom_header')",
            name="ck_tools_auth_type",
        ),
        Index("idx_tools_workspace_id", "workspace_id"),
        Index("idx_tools_type", "type"),
        Index("idx_tools_category", "category"),
        Index("idx_tools_status", "status"),
        Index("idx_tools_input_schema_gin", "input_schema", postgresql_using="gin"),
    )

    # NULL workspace_id => global builtin (visible to every workspace).
    workspace_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    icon: Mapped[str | None] = mapped_column(String(120), nullable=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="general")

    type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")

    # Latest published version number. Snapshots live in tool_versions.
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    input_schema: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    output_schema: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    # Per-type config: HttpToolConfig | MessagingToolConfig | etc.
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    # Auth shape:
    #   {"type": "bearer", "secret_refs": ["slack_bot_token"]}
    auth_type: Mapped[str] = mapped_column(String(32), nullable=False, default="none")
    auth_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    # References (not values) of secrets stored in app.modules.secrets.
    # Shape: {"ZENDESK_TOKEN": "secret_id_abc", ...}
    secret_refs: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    # Guardrails — enforced by the executor:
    #   {"requires_human_approval": bool, "confirmation_message": str,
    #    "allowed_domains": [...], "blocked_domains": [...],
    #    "rate_limit_per_minute": int, "allow_destructive_action": bool}
    guardrails: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    # Execution policy — retry / timeout / fallback:
    #   {"timeout_ms": 10000, "retry_count": 0, "retry_backoff_ms": 500,
    #    "continue_on_failure": false, "fallback_tool_id": null}
    execution_policy: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    # Where this tool is exposed:
    #   {"web": true, "slack": true, "telegram": false, "workflow_only": false}
    channel_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    created_by: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )


# ──────────────────────────────────────────────────────────────────────
# ToolVersion — immutable snapshot of a tool at publish time
# ──────────────────────────────────────────────────────────────────────


class ToolVersion(Base, IdMixin, CreatedAtMixin):
    """Snapshot of a Tool config + schemas, so workflow runs pinned to an
    older version keep executing the original behaviour after the live
    tool changes.

    Workflow nodes reference ``tool_version_id`` (not just ``tool_id``)
    so a redeployed tool can't silently change a running pipeline's
    contract."""

    __tablename__ = "tool_versions"
    __table_args__ = (
        UniqueConstraint("tool_id", "version_number", name="uq_tool_versions_tool_version"),
        Index("idx_tool_versions_tool_id", "tool_id"),
    )

    tool_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tools.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)

    input_schema: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    output_schema: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    guardrails: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    execution_policy: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    created_by: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )


# ──────────────────────────────────────────────────────────────────────
# ToolExecution — one row per tool invocation
# ──────────────────────────────────────────────────────────────────────


class ToolExecution(Base, IdMixin, CreatedAtMixin):
    """Async-first execution record.

    Created in ``queued`` state by the dispatcher, advanced to ``running``
    when the executor picks it up, and resolved to one of
    ``success | failed | timeout | cancelled | pending_approval``."""

    __tablename__ = "tool_executions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'success', 'completed', 'failed', "
            "'timeout', 'cancelled', 'pending_approval')",
            name="ck_tool_executions_status",
        ),
        Index("idx_tool_executions_run_id", "run_id"),
        Index("idx_tool_executions_agent_id", "agent_id"),
        Index("idx_tool_executions_tool_id", "tool_id"),
        Index("idx_tool_executions_status", "status"),
        Index("idx_tool_executions_workspace_id", "workspace_id"),
    )

    workspace_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )

    run_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=True,
    )
    run_node_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workflow_run_nodes.id", ondelete="SET NULL"),
        nullable=True,
    )

    tool_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tools.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Pinned snapshot at dispatch time — survives tool edits/deletes.
    tool_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    agent_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )

    tool_name: Mapped[str] = mapped_column(String(120), nullable=False)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")

    input: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    output: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    # Observability — surfaced verbatim in the runs UI.
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float | None] = mapped_column(Numeric(12, 8), nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ──────────────────────────────────────────────────────────────────────
# ToolApproval — gates execution of `requires_human_approval` tools
# ──────────────────────────────────────────────────────────────────────


class ToolApproval(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "tool_approvals"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'expired')",
            name="ck_tool_approvals_status",
        ),
        UniqueConstraint("execution_id", name="uq_tool_approvals_execution"),
        Index("idx_tool_approvals_execution_id", "execution_id"),
        Index("idx_tool_approvals_status", "status"),
    )

    execution_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tool_executions.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    requested_by_agent_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)

    approved_by: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


# ──────────────────────────────────────────────────────────────────────
# ToolExecutionLog — append-only structured log lines per execution
# ──────────────────────────────────────────────────────────────────────


class ToolExecutionLog(Base, IdMixin, CreatedAtMixin):
    __tablename__ = "tool_execution_logs"
    __table_args__ = (
        CheckConstraint(
            "level IN ('debug', 'info', 'warn', 'error')",
            name="ck_tool_execution_logs_level",
        ),
        Index("idx_tool_execution_logs_execution_id", "execution_id"),
        Index(
            "idx_tool_execution_logs_created_at",
            "created_at",
            postgresql_using="btree",
        ),
    )

    execution_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tool_executions.id", ondelete="CASCADE"),
        nullable=False,
    )

    level: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    message: Mapped[str] = mapped_column(Text, nullable=False)

    log_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )


# ──────────────────────────────────────────────────────────────────────
# AgentToolPermission — per-agent toggle + guardrail overrides
# ──────────────────────────────────────────────────────────────────────
#
# Lives in the *agents* table file as ``AgentTool`` (M2M join), but we
# carry the permission *shape* here so the tools module owns the
# vocabulary used at execution time. Service code is responsible for
# wiring the two together — there is no separate table here.
#
# Fields the executor reads off ``AgentTool.config``:
#   - approval_required: bool   (forces a ToolApproval even if the tool
#                                itself doesn't require one)
#   - max_calls_per_run: int    (0 = unlimited)
#   - call_rate_per_minute: int
#   - input_overrides: dict     (default values stamped onto inputs)
