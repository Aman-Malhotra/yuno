"""workflow_webhooks — per-workflow ingress tokens

Per-workflow signed-token surface for external integrations. The public
ingress endpoint at ``POST /api/v1/hooks/{workflow_id}/{token}`` reads this
table to verify incoming requests and enqueue a ``WorkflowRun``.

Revision ID: 0005_workflow_webhooks
Revises: 0004_tools_registry
Create Date: 2026-05-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_workflow_webhooks"
down_revision: str | None = "0004_tools_registry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


NOW = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "workflow_webhooks",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workflow_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workflows.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("token_prefix", sa.String(16), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_ip", sa.String(64), nullable=True),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column(
            "created_by",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.CheckConstraint(
            "status IN ('active', 'revoked')",
            name="ck_workflow_webhooks_status",
        ),
    )
    op.create_index("idx_workflow_webhooks_workflow_id", "workflow_webhooks", ["workflow_id"])
    op.create_index("idx_workflow_webhooks_token_hash", "workflow_webhooks", ["token_hash"])


def downgrade() -> None:
    op.drop_index("idx_workflow_webhooks_token_hash", table_name="workflow_webhooks")
    op.drop_index("idx_workflow_webhooks_workflow_id", table_name="workflow_webhooks")
    op.drop_table("workflow_webhooks")
