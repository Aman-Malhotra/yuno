"""extend tools registry — versions, approvals, logs, guardrails

Brings the `tools` module up to the spec described in the tool-registry
design doc:

- adds tool metadata fields (category, icon, version, auth, guardrails,
  execution_policy, channel_config)
- broadens the `type` CHECK to include `messaging`, `agent_handoff`,
  `webhook`
- snapshots each publish via the new `tool_versions` table so workflow
  runs pinned to a version keep executing the original behaviour
- per-execution observability: duration_ms, retry_count, tokens_used,
  cost_usd
- async-first lifecycle: status now spans `queued | running | success
  | failed | timeout | cancelled | pending_approval`
- `tool_approvals` gates execution of high-risk tools
- `tool_execution_logs` is the append-only log stream rendered in the
  runs UI

Revision ID: 0004_tools_registry
Revises: 0003_user_llm_creds
Create Date: 2026-05-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_tools_registry"
down_revision: str | None = "0003_user_llm_creds"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


JSONB_EMPTY = sa.text("'{}'::jsonb")
NOW = sa.text("now()")


# ──────────────────────────────────────────────────────────────────────
# upgrade
# ──────────────────────────────────────────────────────────────────────


def upgrade() -> None:
    # ── tools: new columns ──────────────────────────────────────────
    op.add_column(
        "tools",
        sa.Column("icon", sa.String(120), nullable=True),
    )
    op.add_column(
        "tools",
        sa.Column(
            "category",
            sa.String(64),
            nullable=False,
            server_default="general",
        ),
    )
    op.add_column(
        "tools",
        sa.Column(
            "version",
            sa.Integer,
            nullable=False,
            server_default="1",
        ),
    )
    op.add_column(
        "tools",
        sa.Column(
            "auth_type",
            sa.String(32),
            nullable=False,
            server_default="none",
        ),
    )
    op.add_column(
        "tools",
        sa.Column(
            "auth_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=JSONB_EMPTY,
        ),
    )
    op.add_column(
        "tools",
        sa.Column(
            "guardrails",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=JSONB_EMPTY,
        ),
    )
    op.add_column(
        "tools",
        sa.Column(
            "execution_policy",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=JSONB_EMPTY,
        ),
    )
    op.add_column(
        "tools",
        sa.Column(
            "channel_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=JSONB_EMPTY,
        ),
    )

    op.create_index("idx_tools_category", "tools", ["category"])
    op.create_index("idx_tools_status", "tools", ["status"])

    # CHECK constraints — replace with broader sets.
    op.drop_constraint("ck_tools_type", "tools", type_="check")
    op.create_check_constraint(
        "ck_tools_type",
        "tools",
        "type IN ('builtin', 'http', 'messaging', 'agent_handoff', 'webhook', 'python', 'mock')",
    )
    op.drop_constraint("ck_tools_status", "tools", type_="check")
    op.create_check_constraint(
        "ck_tools_status",
        "tools",
        "status IN ('draft', 'active', 'disabled', 'archived')",
    )
    op.create_check_constraint(
        "ck_tools_auth_type",
        "tools",
        "auth_type IN ('none', 'bearer', 'api_key', 'basic', 'custom_header')",
    )

    # ── tool_versions: immutable snapshots ──────────────────────────
    op.create_table(
        "tool_versions",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "tool_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tools.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column(
            "input_schema",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=JSONB_EMPTY,
        ),
        sa.Column(
            "output_schema",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=JSONB_EMPTY,
        ),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=JSONB_EMPTY,
        ),
        sa.Column(
            "guardrails",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=JSONB_EMPTY,
        ),
        sa.Column(
            "execution_policy",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=JSONB_EMPTY,
        ),
        sa.Column(
            "snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=JSONB_EMPTY,
        ),
        sa.Column(
            "created_by",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=NOW,
            nullable=False,
        ),
        sa.UniqueConstraint("tool_id", "version_number", name="uq_tool_versions_tool_version"),
    )
    op.create_index("idx_tool_versions_tool_id", "tool_versions", ["tool_id"])

    # ── tool_executions: new columns + broader status ───────────────
    op.add_column(
        "tool_executions",
        sa.Column(
            "tool_version",
            sa.Integer,
            nullable=False,
            server_default="1",
        ),
    )
    op.add_column(
        "tool_executions",
        sa.Column("duration_ms", sa.Integer, nullable=True),
    )
    op.add_column(
        "tool_executions",
        sa.Column(
            "retry_count",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "tool_executions",
        sa.Column("tokens_used", sa.Integer, nullable=True),
    )
    op.add_column(
        "tool_executions",
        sa.Column("cost_usd", sa.Numeric(12, 8), nullable=True),
    )
    op.alter_column(
        "tool_executions",
        "status",
        server_default="queued",
    )
    op.drop_constraint("ck_tool_executions_status", "tool_executions", type_="check")
    op.create_check_constraint(
        "ck_tool_executions_status",
        "tool_executions",
        "status IN ('queued', 'running', 'success', 'completed', 'failed', "
        "'timeout', 'cancelled', 'pending_approval')",
    )
    op.create_index("idx_tool_executions_workspace_id", "tool_executions", ["workspace_id"])

    # ── tool_approvals ───────────────────────────────────────────────
    op.create_table(
        "tool_approvals",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "execution_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tool_executions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "requested_by_agent_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("prompt", sa.Text, nullable=True),
        sa.Column(
            "approved_by",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=NOW,
            nullable=False,
        ),
        sa.UniqueConstraint("execution_id", name="uq_tool_approvals_execution"),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'expired')",
            name="ck_tool_approvals_status",
        ),
    )
    op.create_index("idx_tool_approvals_execution_id", "tool_approvals", ["execution_id"])
    op.create_index("idx_tool_approvals_status", "tool_approvals", ["status"])

    # ── tool_execution_logs ─────────────────────────────────────────
    op.create_table(
        "tool_execution_logs",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "execution_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tool_executions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("level", sa.String(16), nullable=False, server_default="info"),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=JSONB_EMPTY,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=NOW,
            nullable=False,
        ),
        sa.CheckConstraint(
            "level IN ('debug', 'info', 'warn', 'error')",
            name="ck_tool_execution_logs_level",
        ),
    )
    op.create_index(
        "idx_tool_execution_logs_execution_id",
        "tool_execution_logs",
        ["execution_id"],
    )
    op.create_index(
        "idx_tool_execution_logs_created_at",
        "tool_execution_logs",
        ["created_at"],
    )


# ──────────────────────────────────────────────────────────────────────
# downgrade
# ──────────────────────────────────────────────────────────────────────


def downgrade() -> None:
    op.drop_index("idx_tool_execution_logs_created_at", table_name="tool_execution_logs")
    op.drop_index("idx_tool_execution_logs_execution_id", table_name="tool_execution_logs")
    op.drop_table("tool_execution_logs")

    op.drop_index("idx_tool_approvals_status", table_name="tool_approvals")
    op.drop_index("idx_tool_approvals_execution_id", table_name="tool_approvals")
    op.drop_table("tool_approvals")

    # tool_executions
    op.drop_index("idx_tool_executions_workspace_id", table_name="tool_executions")
    op.drop_constraint("ck_tool_executions_status", "tool_executions", type_="check")
    op.create_check_constraint(
        "ck_tool_executions_status",
        "tool_executions",
        "status IN ('running', 'completed', 'failed', 'cancelled')",
    )
    op.alter_column("tool_executions", "status", server_default="running")
    op.drop_column("tool_executions", "cost_usd")
    op.drop_column("tool_executions", "tokens_used")
    op.drop_column("tool_executions", "retry_count")
    op.drop_column("tool_executions", "duration_ms")
    op.drop_column("tool_executions", "tool_version")

    op.drop_index("idx_tool_versions_tool_id", table_name="tool_versions")
    op.drop_table("tool_versions")

    # tools
    op.drop_constraint("ck_tools_auth_type", "tools", type_="check")
    op.drop_constraint("ck_tools_status", "tools", type_="check")
    op.create_check_constraint(
        "ck_tools_status",
        "tools",
        "status IN ('active', 'disabled', 'archived')",
    )
    op.drop_constraint("ck_tools_type", "tools", type_="check")
    op.create_check_constraint(
        "ck_tools_type",
        "tools",
        "type IN ('builtin', 'http', 'python', 'mock')",
    )
    op.drop_index("idx_tools_status", table_name="tools")
    op.drop_index("idx_tools_category", table_name="tools")
    op.drop_column("tools", "channel_config")
    op.drop_column("tools", "execution_policy")
    op.drop_column("tools", "guardrails")
    op.drop_column("tools", "auth_config")
    op.drop_column("tools", "auth_type")
    op.drop_column("tools", "version")
    op.drop_column("tools", "category")
    op.drop_column("tools", "icon")
