"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-23

"""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UUID_DEFAULT = sa.text("gen_random_uuid()")
NOW = sa.text("now()")


def _uuid_pk() -> sa.Column[UUID]:
    return sa.Column(
        "id",
        sa.Uuid(as_uuid=True),
        primary_key=True,
        server_default=UUID_DEFAULT,
        nullable=False,
    )


def _created_at() -> sa.Column[Any]:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=NOW,
        nullable=False,
    )


def _updated_at() -> sa.Column[Any]:
    return sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        server_default=NOW,
        nullable=False,
    )


def _deleted_at() -> sa.Column[Any]:
    return sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # ──────────────────────────────────────────────────────────────────
    # users
    # ──────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        _uuid_pk(),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("hashed_password", sa.Text, nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("is_verified", sa.Boolean, nullable=False, server_default=sa.false()),
        _created_at(),
        _updated_at(),
        _deleted_at(),
    )
    op.create_index("idx_users_email", "users", ["email"])

    # ──────────────────────────────────────────────────────────────────
    # workspaces
    # ──────────────────────────────────────────────────────────────────
    op.create_table(
        "workspaces",
        _uuid_pk(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(120), nullable=False, unique=True),
        _created_at(),
        _updated_at(),
        _deleted_at(),
    )

    # ──────────────────────────────────────────────────────────────────
    # refresh_tokens
    # ──────────────────────────────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        _uuid_pk(),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.Text, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        _created_at(),
    )
    op.create_index("idx_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("idx_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"])

    # ──────────────────────────────────────────────────────────────────
    # workspace_members
    # ──────────────────────────────────────────────────────────────────
    op.create_table(
        "workspace_members",
        _uuid_pk(),
        sa.Column(
            "workspace_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(32), nullable=False),
        _created_at(),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_members_ws_user"),
        sa.CheckConstraint(
            "role IN ('owner', 'admin', 'member', 'viewer')",
            name="ck_workspace_members_role",
        ),
    )
    op.create_index("idx_workspace_members_workspace_id", "workspace_members", ["workspace_id"])
    op.create_index("idx_workspace_members_user_id", "workspace_members", ["user_id"])

    # ──────────────────────────────────────────────────────────────────
    # agents
    # ──────────────────────────────────────────────────────────────────
    op.create_table(
        "agents",
        _uuid_pk(),
        sa.Column(
            "workspace_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("role", sa.String(120), nullable=False),
        sa.Column("system_prompt", sa.Text, nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("model_provider", sa.String(64), nullable=False),
        sa.Column("model_name", sa.String(120), nullable=False),
        sa.Column("temperature", sa.Numeric(3, 2), nullable=False, server_default=sa.text("0.70")),
        sa.Column("max_tokens", sa.Integer, nullable=True),
        sa.Column("top_p", sa.Numeric(3, 2), nullable=True),
        sa.Column("memory_config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("schedule_config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("guardrails_config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("interaction_rules", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("limits_config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("skills_config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        _created_at(),
        _updated_at(),
        _deleted_at(),
        sa.UniqueConstraint("workspace_id", "slug", name="uq_agents_workspace_slug"),
        sa.CheckConstraint("status IN ('draft', 'active', 'archived')", name="ck_agents_status"),
    )
    op.create_index("idx_agents_workspace_id", "agents", ["workspace_id"])
    op.create_index("idx_agents_status", "agents", ["status"])
    op.create_index("idx_agents_model_provider", "agents", ["model_provider"])
    op.create_index("idx_agents_metadata_gin", "agents", ["metadata"], postgresql_using="gin")
    op.create_index(
        "idx_agents_memory_config_gin", "agents", ["memory_config"], postgresql_using="gin"
    )

    # ──────────────────────────────────────────────────────────────────
    # tools
    # ──────────────────────────────────────────────────────────────────
    op.create_table(
        "tools",
        _uuid_pk(),
        sa.Column(
            "workspace_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("input_schema", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("output_schema", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("secret_refs", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_by",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        _created_at(),
        _updated_at(),
        _deleted_at(),
        sa.UniqueConstraint("workspace_id", "slug", name="uq_tools_workspace_slug"),
        sa.CheckConstraint("type IN ('builtin', 'http', 'python', 'mock')", name="ck_tools_type"),
        sa.CheckConstraint("status IN ('active', 'disabled', 'archived')", name="ck_tools_status"),
    )
    op.create_index("idx_tools_workspace_id", "tools", ["workspace_id"])
    op.create_index("idx_tools_type", "tools", ["type"])
    op.create_index("idx_tools_input_schema_gin", "tools", ["input_schema"], postgresql_using="gin")

    # ──────────────────────────────────────────────────────────────────
    # agent_versions
    # ──────────────────────────────────────────────────────────────────
    op.create_table(
        "agent_versions",
        _uuid_pk(),
        sa.Column(
            "agent_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(120), nullable=False),
        sa.Column("system_prompt", sa.Text, nullable=False),
        sa.Column("model_provider", sa.String(64), nullable=False),
        sa.Column("model_name", sa.String(120), nullable=False),
        sa.Column("temperature", sa.Numeric(3, 2), nullable=True),
        sa.Column("max_tokens", sa.Integer, nullable=True),
        sa.Column("top_p", sa.Numeric(3, 2), nullable=True),
        sa.Column("memory_config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("guardrails_config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("interaction_rules", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("limits_config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("skills_config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("snapshot", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_by",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        _created_at(),
        sa.UniqueConstraint("agent_id", "version_number", name="uq_agent_versions_agent_version"),
    )
    op.create_index("idx_agent_versions_agent_id", "agent_versions", ["agent_id"])

    # ──────────────────────────────────────────────────────────────────
    # agent_tools
    # ──────────────────────────────────────────────────────────────────
    op.create_table(
        "agent_tools",
        _uuid_pk(),
        sa.Column(
            "agent_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tool_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tools.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default="{}"),
        _created_at(),
        sa.UniqueConstraint("agent_id", "tool_id", name="uq_agent_tools_agent_tool"),
    )
    op.create_index("idx_agent_tools_agent_id", "agent_tools", ["agent_id"])
    op.create_index("idx_agent_tools_tool_id", "agent_tools", ["tool_id"])

    # ──────────────────────────────────────────────────────────────────
    # llm_provider_configs
    # ──────────────────────────────────────────────────────────────────
    op.create_table(
        "llm_provider_configs",
        _uuid_pk(),
        sa.Column(
            "workspace_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("api_key_secret_ref", sa.Text, nullable=True),
        sa.Column("base_url", sa.Text, nullable=True),
        sa.Column("default_model", sa.String(120), nullable=True),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_by",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        _created_at(),
        _updated_at(),
        sa.UniqueConstraint(
            "workspace_id",
            "provider",
            "display_name",
            name="uq_llm_provider_configs_ws_provider_name",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'disabled')", name="ck_llm_provider_configs_status"
        ),
    )
    op.create_index(
        "idx_llm_provider_configs_workspace_id", "llm_provider_configs", ["workspace_id"]
    )
    op.create_index("idx_llm_provider_configs_provider", "llm_provider_configs", ["provider"])

    # ──────────────────────────────────────────────────────────────────
    # llm_model_catalog
    # ──────────────────────────────────────────────────────────────────
    op.create_table(
        "llm_model_catalog",
        _uuid_pk(),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("model_name", sa.String(120), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("supports_tools", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("supports_streaming", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("supports_json_mode", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("supports_vision", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("input_token_cost_usd", sa.Numeric(12, 8), nullable=True),
        sa.Column("output_token_cost_usd", sa.Numeric(12, 8), nullable=True),
        sa.Column("context_window_tokens", sa.Integer, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        _created_at(),
        _updated_at(),
        sa.UniqueConstraint("provider", "model_name", name="uq_llm_model_catalog_provider_model"),
    )

    # ──────────────────────────────────────────────────────────────────
    # workflows
    # ──────────────────────────────────────────────────────────────────
    op.create_table(
        "workflows",
        _uuid_pk(),
        sa.Column(
            "workspace_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("graph_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("compiled_graph", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("settings", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("published_version_id", sa.Uuid(as_uuid=True), nullable=True),
        _created_at(),
        _updated_at(),
        _deleted_at(),
        sa.UniqueConstraint("workspace_id", "slug", name="uq_workflows_workspace_slug"),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'archived')", name="ck_workflows_status"
        ),
    )
    op.create_index("idx_workflows_workspace_id", "workflows", ["workspace_id"])
    op.create_index("idx_workflows_status", "workflows", ["status"])
    op.create_index(
        "idx_workflows_graph_json_gin", "workflows", ["graph_json"], postgresql_using="gin"
    )

    # ──────────────────────────────────────────────────────────────────
    # workflow_versions
    # ──────────────────────────────────────────────────────────────────
    op.create_table(
        "workflow_versions",
        _uuid_pk(),
        sa.Column(
            "workflow_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workflows.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("graph_json", postgresql.JSONB, nullable=False),
        sa.Column("compiled_graph", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("settings", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_by",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        _created_at(),
        sa.UniqueConstraint(
            "workflow_id", "version_number", name="uq_workflow_versions_workflow_version"
        ),
    )
    op.create_index("idx_workflow_versions_workflow_id", "workflow_versions", ["workflow_id"])

    # ──────────────────────────────────────────────────────────────────
    # workflow_templates
    # ──────────────────────────────────────────────────────────────────
    op.create_table(
        "workflow_templates",
        _uuid_pk(),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(120), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("graph_json", postgresql.JSONB, nullable=False),
        sa.Column("required_agents", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("required_tools", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("is_system_template", sa.Boolean, nullable=False, server_default=sa.true()),
        _created_at(),
        _updated_at(),
    )

    # ──────────────────────────────────────────────────────────────────
    # workflow_runs
    # ──────────────────────────────────────────────────────────────────
    op.create_table(
        "workflow_runs",
        _uuid_pk(),
        sa.Column(
            "workspace_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workflow_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workflows.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "workflow_version_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workflow_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "triggered_by_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("trigger_type", sa.String(32), nullable=False),
        sa.Column("trigger_source", sa.String(120), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("input", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("output", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("error_details", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("total_input_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_output_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_cost_usd", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        _created_at(),
        _updated_at(),
        sa.CheckConstraint(
            "trigger_type IN ('manual', 'schedule', 'channel', 'api', 'test')",
            name="ck_workflow_runs_trigger_type",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'waiting', 'completed', 'failed', 'cancelled')",
            name="ck_workflow_runs_status",
        ),
    )
    op.create_index("idx_workflow_runs_workspace_id", "workflow_runs", ["workspace_id"])
    op.create_index("idx_workflow_runs_workflow_id", "workflow_runs", ["workflow_id"])
    op.create_index("idx_workflow_runs_status", "workflow_runs", ["status"])
    op.create_index("idx_workflow_runs_created_at", "workflow_runs", [sa.text("created_at DESC")])

    # ──────────────────────────────────────────────────────────────────
    # workflow_run_nodes
    # ──────────────────────────────────────────────────────────────────
    op.create_table(
        "workflow_run_nodes",
        _uuid_pk(),
        sa.Column(
            "run_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("node_id", sa.String(120), nullable=False),
        sa.Column("node_type", sa.String(64), nullable=False),
        sa.Column("node_label", sa.String(255), nullable=True),
        sa.Column(
            "agent_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "agent_version_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("agent_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "tool_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tools.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("input", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("output", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("error_details", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        _created_at(),
        _updated_at(),
        sa.UniqueConstraint("run_id", "node_id", name="uq_workflow_run_nodes_run_node"),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'waiting', 'completed', 'failed', 'skipped', 'cancelled')",
            name="ck_workflow_run_nodes_status",
        ),
    )
    op.create_index("idx_workflow_run_nodes_run_id", "workflow_run_nodes", ["run_id"])
    op.create_index("idx_workflow_run_nodes_status", "workflow_run_nodes", ["status"])
    op.create_index("idx_workflow_run_nodes_agent_id", "workflow_run_nodes", ["agent_id"])

    # ──────────────────────────────────────────────────────────────────
    # runtime_events
    # ──────────────────────────────────────────────────────────────────
    op.create_table(
        "runtime_events",
        _uuid_pk(),
        sa.Column(
            "workspace_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_node_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workflow_run_nodes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("node_id", sa.String(120), nullable=True),
        sa.Column(
            "agent_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "tool_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tools.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("sequence_number", sa.BigInteger, nullable=False),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default="{}"),
        _created_at(),
        sa.UniqueConstraint("run_id", "sequence_number", name="uq_runtime_events_run_seq"),
    )
    op.create_index(
        "idx_runtime_events_run_id_seq", "runtime_events", ["run_id", "sequence_number"]
    )
    op.create_index("idx_runtime_events_workspace_id", "runtime_events", ["workspace_id"])
    op.create_index("idx_runtime_events_event_type", "runtime_events", ["event_type"])
    op.create_index("idx_runtime_events_created_at", "runtime_events", [sa.text("created_at DESC")])
    op.create_index(
        "idx_runtime_events_payload_gin", "runtime_events", ["payload"], postgresql_using="gin"
    )

    # ──────────────────────────────────────────────────────────────────
    # agent_messages
    # ──────────────────────────────────────────────────────────────────
    op.create_table(
        "agent_messages",
        _uuid_pk(),
        sa.Column(
            "workspace_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workflow_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "run_node_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workflow_run_nodes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("conversation_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("direction", sa.String(16), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column(
            "from_agent_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "to_agent_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "from_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("channel_type", sa.String(32), nullable=True),
        sa.Column("external_channel_id", sa.String(255), nullable=True),
        sa.Column("external_message_id", sa.String(255), nullable=True),
        sa.Column("external_user_id", sa.String(255), nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("content_type", sa.String(16), nullable=False, server_default="text"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        _created_at(),
        sa.CheckConstraint(
            "direction IN ('inbound', 'outbound', 'internal')",
            name="ck_agent_messages_direction",
        ),
        sa.CheckConstraint(
            "role IN ('system', 'user', 'assistant', 'tool', 'agent')",
            name="ck_agent_messages_role",
        ),
        sa.CheckConstraint(
            "content_type IN ('text', 'json', 'markdown', 'image', 'file')",
            name="ck_agent_messages_content_type",
        ),
    )
    op.create_index("idx_agent_messages_workspace_id", "agent_messages", ["workspace_id"])
    op.create_index("idx_agent_messages_run_id", "agent_messages", ["run_id"])
    op.create_index("idx_agent_messages_conversation_id", "agent_messages", ["conversation_id"])
    op.create_index("idx_agent_messages_from_agent_id", "agent_messages", ["from_agent_id"])
    op.create_index("idx_agent_messages_to_agent_id", "agent_messages", ["to_agent_id"])
    op.create_index("idx_agent_messages_created_at", "agent_messages", [sa.text("created_at DESC")])
    op.create_index(
        "idx_agent_messages_metadata_gin", "agent_messages", ["metadata"], postgresql_using="gin"
    )

    # ──────────────────────────────────────────────────────────────────
    # tool_executions
    # ──────────────────────────────────────────────────────────────────
    op.create_table(
        "tool_executions",
        _uuid_pk(),
        sa.Column(
            "workspace_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "run_node_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workflow_run_nodes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "tool_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tools.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "agent_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("tool_name", sa.String(120), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="running"),
        sa.Column("input", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("output", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("error_details", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=NOW,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        _created_at(),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'failed', 'cancelled')",
            name="ck_tool_executions_status",
        ),
    )
    op.create_index("idx_tool_executions_run_id", "tool_executions", ["run_id"])
    op.create_index("idx_tool_executions_agent_id", "tool_executions", ["agent_id"])
    op.create_index("idx_tool_executions_tool_id", "tool_executions", ["tool_id"])
    op.create_index("idx_tool_executions_status", "tool_executions", ["status"])

    # ──────────────────────────────────────────────────────────────────
    # llm_calls
    # ──────────────────────────────────────────────────────────────────
    op.create_table(
        "llm_calls",
        _uuid_pk(),
        sa.Column(
            "workspace_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workflow_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "run_node_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workflow_run_nodes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "agent_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("model_name", sa.String(120), nullable=False),
        sa.Column("request_type", sa.String(32), nullable=False, server_default="chat"),
        sa.Column("status", sa.String(32), nullable=False, server_default="running"),
        sa.Column("input_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("input_cost_usd", sa.Numeric(12, 8), nullable=False, server_default="0"),
        sa.Column("output_cost_usd", sa.Numeric(12, 8), nullable=False, server_default="0"),
        sa.Column("total_cost_usd", sa.Numeric(12, 8), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("request_payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("response_payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("error_details", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=NOW,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        _created_at(),
        sa.CheckConstraint(
            "request_type IN ('chat', 'completion', 'embedding', 'rerank')",
            name="ck_llm_calls_request_type",
        ),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'failed', 'cancelled')",
            name="ck_llm_calls_status",
        ),
    )
    op.create_index("idx_llm_calls_workspace_id", "llm_calls", ["workspace_id"])
    op.create_index("idx_llm_calls_run_id", "llm_calls", ["run_id"])
    op.create_index("idx_llm_calls_agent_id", "llm_calls", ["agent_id"])
    op.create_index("idx_llm_calls_provider_model", "llm_calls", ["provider", "model_name"])
    op.create_index("idx_llm_calls_created_at", "llm_calls", [sa.text("created_at DESC")])

    # ──────────────────────────────────────────────────────────────────
    # channel_connections
    # ──────────────────────────────────────────────────────────────────
    op.create_table(
        "channel_connections",
        _uuid_pk(),
        sa.Column(
            "workspace_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "agent_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("channel_type", sa.String(32), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("external_bot_id", sa.String(255), nullable=True),
        sa.Column("external_workspace_id", sa.String(255), nullable=True),
        sa.Column("external_channel_id", sa.String(255), nullable=True),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("secret_refs", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("last_connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        _created_at(),
        _updated_at(),
        _deleted_at(),
        sa.CheckConstraint(
            "channel_type IN ('telegram', 'slack', 'whatsapp')",
            name="ck_channel_connections_channel_type",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'disabled', 'error')",
            name="ck_channel_connections_status",
        ),
    )
    op.create_index("idx_channel_connections_workspace_id", "channel_connections", ["workspace_id"])
    op.create_index("idx_channel_connections_agent_id", "channel_connections", ["agent_id"])
    op.create_index("idx_channel_connections_channel_type", "channel_connections", ["channel_type"])

    # ──────────────────────────────────────────────────────────────────
    # channel_messages
    # ──────────────────────────────────────────────────────────────────
    op.create_table(
        "channel_messages",
        _uuid_pk(),
        sa.Column(
            "workspace_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "channel_connection_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("channel_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "agent_message_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("agent_messages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("channel_type", sa.String(32), nullable=False),
        sa.Column("direction", sa.String(16), nullable=False),
        sa.Column("external_chat_id", sa.String(255), nullable=False),
        sa.Column("external_message_id", sa.String(255), nullable=True),
        sa.Column("external_user_id", sa.String(255), nullable=True),
        sa.Column("text", sa.Text, nullable=True),
        sa.Column("raw_payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_error", sa.Text, nullable=True),
        _created_at(),
        sa.CheckConstraint(
            "direction IN ('inbound', 'outbound')",
            name="ck_channel_messages_direction",
        ),
    )
    op.create_index(
        "idx_channel_messages_connection_id", "channel_messages", ["channel_connection_id"]
    )
    op.create_index(
        "idx_channel_messages_external_chat_id", "channel_messages", ["external_chat_id"]
    )
    op.create_index(
        "idx_channel_messages_created_at", "channel_messages", [sa.text("created_at DESC")]
    )

    # ──────────────────────────────────────────────────────────────────
    # agent_memories
    # ──────────────────────────────────────────────────────────────────
    op.create_table(
        "agent_memories",
        _uuid_pk(),
        sa.Column(
            "workspace_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "agent_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("memory_type", sa.String(32), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("source_type", sa.String(32), nullable=True),
        sa.Column("source_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column(
            "importance_score",
            sa.Numeric(4, 3),
            nullable=False,
            server_default="0.500",
        ),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        _created_at(),
        _updated_at(),
        sa.CheckConstraint(
            "memory_type IN ('summary', 'fact', 'preference', 'conversation', 'vector')",
            name="ck_agent_memories_memory_type",
        ),
    )
    op.create_index("idx_agent_memories_agent_id", "agent_memories", ["agent_id"])
    op.create_index("idx_agent_memories_workspace_id", "agent_memories", ["workspace_id"])
    op.create_index("idx_agent_memories_memory_type", "agent_memories", ["memory_type"])
    op.create_index(
        "idx_agent_memories_metadata_gin", "agent_memories", ["metadata"], postgresql_using="gin"
    )

    # ──────────────────────────────────────────────────────────────────
    # schedules
    # ──────────────────────────────────────────────────────────────────
    op.create_table(
        "schedules",
        _uuid_pk(),
        sa.Column(
            "workspace_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "agent_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "workflow_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workflows.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("schedule_type", sa.String(32), nullable=False),
        sa.Column("cron_expression", sa.Text, nullable=True),
        sa.Column("interval_seconds", sa.Integer, nullable=True),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
        sa.Column("input", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        _created_at(),
        _updated_at(),
        _deleted_at(),
        sa.CheckConstraint(
            "schedule_type IN ('cron', 'interval', 'one_time')",
            name="ck_schedules_schedule_type",
        ),
        sa.CheckConstraint(
            "agent_id IS NOT NULL OR workflow_id IS NOT NULL",
            name="ck_schedules_target_present",
        ),
    )
    op.create_index("idx_schedules_workspace_id", "schedules", ["workspace_id"])
    op.create_index("idx_schedules_next_run_at", "schedules", ["next_run_at"])
    op.create_index("idx_schedules_is_enabled", "schedules", ["is_enabled"])

    # ──────────────────────────────────────────────────────────────────
    # audit_logs
    # ──────────────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        _uuid_pk(),
        sa.Column(
            "workspace_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "actor_user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("before", postgresql.JSONB, nullable=True),
        sa.Column("after", postgresql.JSONB, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        _created_at(),
    )
    op.create_index("idx_audit_logs_workspace_id", "audit_logs", ["workspace_id"])
    op.create_index("idx_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    op.create_index("idx_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("idx_audit_logs_created_at", "audit_logs", [sa.text("created_at DESC")])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("schedules")
    op.drop_table("agent_memories")
    op.drop_table("channel_messages")
    op.drop_table("channel_connections")
    op.drop_table("llm_calls")
    op.drop_table("tool_executions")
    op.drop_table("agent_messages")
    op.drop_table("runtime_events")
    op.drop_table("workflow_run_nodes")
    op.drop_table("workflow_runs")
    op.drop_table("workflow_templates")
    op.drop_table("workflow_versions")
    op.drop_table("workflows")
    op.drop_table("llm_model_catalog")
    op.drop_table("llm_provider_configs")
    op.drop_table("agent_tools")
    op.drop_table("agent_versions")
    op.drop_table("tools")
    op.drop_table("agents")
    op.drop_table("workspace_members")
    op.drop_table("refresh_tokens")
    op.drop_table("workspaces")
    op.drop_table("users")
