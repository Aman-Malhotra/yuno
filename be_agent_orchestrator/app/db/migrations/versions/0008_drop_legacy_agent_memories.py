"""drop legacy agent_memories table

Original ``agent_memories`` table (defined in 0001_initial) was intended
as a generic long-term store but was never wired — the runtime, services,
routers, and FE never touched it. Long-term memory now lives in
``agent_memories_mem0`` (managed by mem0 directly via pgvector).

Dropping in this migration so the schema stops carrying dead weight.
The migration is destructive — rows are gone after this — but the table
was empty in every deployment so nothing real is lost.

Revision ID: 0008_drop_legacy_agent_memories
Revises: 0007_workspace_llm_credentials
Create Date: 2026-05-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0008_drop_legacy_agent_memories"
down_revision: str | None = "0007_workspace_llm_credentials"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NOW = sa.text("now()")


def upgrade() -> None:
    # Indexes drop with the table via CASCADE, but be explicit so the
    # downgrade can rebuild them identically.
    op.execute("DROP TABLE IF EXISTS agent_memories CASCADE")


def downgrade() -> None:
    """Rebuild the original table shape (from 0001_initial). Rows aren't
    restored — they were dropped in the upgrade."""

    op.create_table(
        "agent_memories",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
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
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.CheckConstraint(
            "memory_type IN ('summary', 'fact', 'preference', 'conversation', 'vector')",
            name="ck_agent_memories_memory_type",
        ),
    )
    op.create_index("idx_agent_memories_agent_id", "agent_memories", ["agent_id"])
    op.create_index("idx_agent_memories_workspace_id", "agent_memories", ["workspace_id"])
    op.create_index("idx_agent_memories_memory_type", "agent_memories", ["memory_type"])
    op.create_index(
        "idx_agent_memories_metadata_gin",
        "agent_memories",
        ["metadata"],
        postgresql_using="gin",
    )
