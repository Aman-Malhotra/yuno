"""add agents.provider_credentials JSONB

Per-agent BYOK (bring your own key) support. An agent may carry its own
LLM provider credentials (``{"api_key": "...", "base_url": "...",
"organization": "..."}``); these override the server-level keys in
settings at dispatch time. Empty default ``{}`` means "use the global key".

Revision ID: 0002_agent_byok_creds
Revises: 0001_initial
Create Date: 2026-05-24

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_agent_byok_creds"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column(
            "provider_credentials",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("agents", "provider_credentials")
