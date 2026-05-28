"""pgvector extension — long-term memory backend

Enables the ``vector`` extension so mem0's pgvector store can create its
embedding column. mem0 manages its own ``memories`` table at runtime; we
only need the extension available on the same Postgres instance.

Image switch (docker-compose) is the other half: ``pgvector/pgvector:pg16``
ships the binary; this migration just registers it on the DB.

Revision ID: 0006_pgvector_extension
Revises: 0005_workflow_webhooks
Create Date: 2026-05-25

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006_pgvector_extension"
down_revision: str | None = "0005_workflow_webhooks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    # Intentionally not dropped — mem0's own tables would break if extension
    # disappears under them. Drop manually if you truly want to remove it.
    pass
