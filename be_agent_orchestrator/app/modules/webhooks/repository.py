from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.webhooks.models import WorkflowWebhook


class WebhookRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        *,
        workspace_id: UUID,
        workflow_id: UUID,
        name: str,
        token_prefix: str,
        token_hash: str,
        created_by: UUID | None,
    ) -> WorkflowWebhook:
        webhook = WorkflowWebhook(
            workspace_id=workspace_id,
            workflow_id=workflow_id,
            name=name,
            status="active",
            token_prefix=token_prefix,
            token_hash=token_hash,
            created_by=created_by,
        )
        self.db.add(webhook)
        await self.db.commit()
        await self.db.refresh(webhook)
        return webhook

    async def list_for_workflow(
        self,
        workspace_id: UUID,
        workflow_id: UUID,
    ) -> list[WorkflowWebhook]:
        stmt = (
            select(WorkflowWebhook)
            .where(
                WorkflowWebhook.workspace_id == workspace_id,
                WorkflowWebhook.workflow_id == workflow_id,
            )
            .order_by(WorkflowWebhook.created_at.desc())
        )
        return list((await self.db.execute(stmt)).scalars())

    async def get_in_workspace(
        self,
        workspace_id: UUID,
        webhook_id: UUID,
    ) -> WorkflowWebhook | None:
        stmt = select(WorkflowWebhook).where(
            WorkflowWebhook.id == webhook_id,
            WorkflowWebhook.workspace_id == workspace_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def find_active_by_hash(
        self,
        workflow_id: UUID,
        token_hash: str,
    ) -> WorkflowWebhook | None:
        """Public-ingress lookup. Workflow id + hash + active status all required.

        We scope by workflow_id (from the URL path) so a leaked token on
        workflow A can't be replayed against workflow B even by accident.
        """

        stmt = select(WorkflowWebhook).where(
            WorkflowWebhook.workflow_id == workflow_id,
            WorkflowWebhook.token_hash == token_hash,
            WorkflowWebhook.status == "active",
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def revoke(self, webhook: WorkflowWebhook) -> WorkflowWebhook:
        webhook.status = "revoked"
        await self.db.commit()
        await self.db.refresh(webhook)
        return webhook

    async def mark_used(
        self,
        webhook: WorkflowWebhook,
        *,
        ip: str | None,
        error: str | None = None,
    ) -> None:
        webhook.last_used_at = datetime.now(UTC)
        webhook.last_used_ip = ip
        webhook.last_error = error
        await self.db.commit()
