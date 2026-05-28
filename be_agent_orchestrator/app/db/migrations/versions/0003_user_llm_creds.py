"""add user_llm_credentials table

Per-user LLM provider credential vault. A user saves their OpenAI / Gemini
/ Groq keys once; every agent they create reuses them automatically
(unless the agent carries its own BYOK creds, which override the vault).

Revision ID: 0003_user_llm_creds
Revises: 0002_agent_byok_creds
Create Date: 2026-05-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_user_llm_creds"
down_revision: str | None = "0002_agent_byok_creds"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_llm_credentials",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column(
            "credentials",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "provider", name="uq_user_llm_creds_user_provider"),
    )
    op.create_index("idx_user_llm_creds_user_id", "user_llm_credentials", ["user_id"])


def downgrade() -> None:
    op.drop_index("idx_user_llm_creds_user_id", table_name="user_llm_credentials")
    op.drop_table("user_llm_credentials")
