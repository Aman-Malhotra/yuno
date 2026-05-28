"""Per-workflow webhook ingress tokens.

Each workflow can carry one or more webhook tokens. External integrations
POST to ``/api/v1/hooks/{workflow_id}/{token}`` to start a run — the public
ingress endpoint verifies the token, enqueues a ``WorkflowRun`` with the
request body as the initial state, and returns 202.

Tokens are stored hashed (constant-time compare via the password hasher).
We also keep an 8-char prefix in plaintext so the UI can say "token …a3f9"
without exposing the secret.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin


class WorkflowWebhook(Base, IdMixin, TimestampMixin):
    __tablename__ = "workflow_webhooks"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'revoked')",
            name="ck_workflow_webhooks_status",
        ),
        # Hash-based lookup index (the public ingress hits this on every request).
        Index("idx_workflow_webhooks_workflow_id", "workflow_id"),
        Index("idx_workflow_webhooks_token_hash", "token_hash"),
    )

    workspace_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    workflow_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")

    # First 8 chars of the plaintext token — safe to show in the UI for
    # disambiguation ("ends in …a3f9"). Never enough to authenticate.
    token_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    # SHA-256 of the full token; lookup is by direct hash equality. We use
    # SHA-256 (not bcrypt) because (a) tokens are already 32 bytes of CSPRNG
    # entropy, no brute-force concern, and (b) we need O(1) DB lookup, not
    # an iterate-and-verify-each-row scheme.
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)

    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
