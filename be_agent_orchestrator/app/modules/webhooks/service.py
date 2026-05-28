"""Webhook lifecycle + verification.

Tokens are 32-byte CSPRNG values base64url-encoded with a ``wfh_`` prefix
("workflow hook"). The prefix makes them grep-able in logs and easy to
detect in leak-scanning tools. We store SHA-256(token) for O(1) lookup;
the plaintext is shown to the user exactly once at creation.
"""

import hashlib
import secrets
from uuid import UUID

import structlog

from app.core.errors import NotFoundError, ValidationError
from app.modules.webhooks.models import WorkflowWebhook
from app.modules.webhooks.repository import WebhookRepository
from app.modules.webhooks.schemas import CreateWebhookRequest
from app.modules.workflows.service import WorkflowService
from app.modules.workspaces.service import WorkspaceService

log = structlog.get_logger("webhooks")

TOKEN_PREFIX = "wfh_"
TOKEN_ENTROPY_BYTES = 32
MAX_ACTIVE_WEBHOOKS_PER_WORKFLOW = 10


def _hash_token(token: str) -> str:
    """Constant-time-safe lookup hash. SHA-256 is fine here because tokens
    already carry 256 bits of CSPRNG entropy — no slow KDF needed."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _generate_token() -> tuple[str, str, str]:
    """Returns ``(plaintext_token, token_prefix, token_hash)``."""

    body = secrets.token_urlsafe(TOKEN_ENTROPY_BYTES)
    token = f"{TOKEN_PREFIX}{body}"
    return token, token[:8], _hash_token(token)


class WebhookService:
    def __init__(
        self,
        repository: WebhookRepository,
        workspace_service: WorkspaceService,
        workflow_service: WorkflowService,
    ) -> None:
        self.repository = repository
        self.workspace_service = workspace_service
        self.workflow_service = workflow_service

    # ──────────────────────────────────────────────────────────────────
    # Management — auth + workspace ACL gated
    # ──────────────────────────────────────────────────────────────────

    async def list_for_workflow(
        self,
        workspace_id: UUID,
        workflow_id: UUID,
        user_id: UUID,
    ) -> list[WorkflowWebhook]:
        # Authorize via the workflow service (also enforces workspace membership).
        await self.workflow_service.get_in_workspace_for_user(workspace_id, workflow_id, user_id)
        return await self.repository.list_for_workflow(workspace_id, workflow_id)

    async def create_for_workflow(
        self,
        workspace_id: UUID,
        workflow_id: UUID,
        user_id: UUID,
        payload: CreateWebhookRequest,
    ) -> tuple[WorkflowWebhook, str]:
        await self.workflow_service.get_in_workspace_for_user(workspace_id, workflow_id, user_id)

        existing = await self.repository.list_for_workflow(workspace_id, workflow_id)
        active = [w for w in existing if w.status == "active"]
        if len(active) >= MAX_ACTIVE_WEBHOOKS_PER_WORKFLOW:
            raise ValidationError(
                "too_many_active_webhooks",
                f"At most {MAX_ACTIVE_WEBHOOKS_PER_WORKFLOW} active webhooks per workflow. "
                "Revoke an old one before minting a new token.",
                {"active_count": len(active)},
            )

        token, prefix, token_hash = _generate_token()
        webhook = await self.repository.create(
            workspace_id=workspace_id,
            workflow_id=workflow_id,
            name=payload.name,
            token_prefix=prefix,
            token_hash=token_hash,
            created_by=user_id,
        )
        log.info(
            "webhook.created",
            webhook_id=str(webhook.id),
            workspace_id=str(workspace_id),
            workflow_id=str(workflow_id),
            created_by=str(user_id),
            name=payload.name,
        )
        return webhook, token

    async def revoke_for_workflow(
        self,
        workspace_id: UUID,
        workflow_id: UUID,
        webhook_id: UUID,
        user_id: UUID,
    ) -> WorkflowWebhook:
        await self.workflow_service.get_in_workspace_for_user(workspace_id, workflow_id, user_id)
        webhook = await self.repository.get_in_workspace(workspace_id, webhook_id)
        if webhook is None or webhook.workflow_id != workflow_id:
            raise NotFoundError(
                "webhook_not_found",
                "Webhook does not exist on this workflow.",
                {"webhook_id": str(webhook_id)},
            )
        if webhook.status == "revoked":
            return webhook
        webhook = await self.repository.revoke(webhook)
        log.info(
            "webhook.revoked",
            webhook_id=str(webhook.id),
            workspace_id=str(workspace_id),
            workflow_id=str(workflow_id),
            actor_user_id=str(user_id),
        )
        return webhook

    # ──────────────────────────────────────────────────────────────────
    # Verification — used by the public ingress endpoint (no auth)
    # ──────────────────────────────────────────────────────────────────

    async def verify(self, workflow_id: UUID, token: str) -> WorkflowWebhook | None:
        """Returns the matching active webhook row, or None.

        Always returns None on bad input — never raises — so callers can
        respond with a single uniform 404 and not leak which factor failed.
        """

        if not token or not token.startswith(TOKEN_PREFIX):
            return None
        token_hash = _hash_token(token)
        return await self.repository.find_active_by_hash(workflow_id, token_hash)

    async def mark_used(
        self,
        webhook: WorkflowWebhook,
        *,
        ip: str | None,
        error: str | None = None,
    ) -> None:
        await self.repository.mark_used(webhook, ip=ip, error=error)
