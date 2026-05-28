"""workspace_llm_credentials — shared LLM keys at workspace scope

One row per ``(workspace_id, provider)``. The agent runtime resolves keys
in this order at run time:

    agent.provider_credentials.api_key  → workspace_llm_credentials  → fail

Same JSONB credentials shape as ``user_llm_credentials``
(``{"api_key": "...", "base_url": "...", "organization": "..."}``) so the
provider clients can swap their key source without caring where it came from.

Revision ID: 0007_workspace_llm_credentials
Revises: 0006_pgvector_extension
Create Date: 2026-05-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0007_workspace_llm_credentials"
down_revision: str | None = "0006_pgvector_extension"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NOW = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "workspace_llm_credentials",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column(
            "credentials",
            JSONB,
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_by",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.UniqueConstraint(
            "workspace_id", "provider", name="uq_workspace_llm_creds_workspace_provider"
        ),
    )
    op.create_index(
        "idx_workspace_llm_creds_workspace_id",
        "workspace_llm_credentials",
        ["workspace_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_workspace_llm_creds_workspace_id", table_name="workspace_llm_credentials")
    op.drop_table("workspace_llm_credentials")
