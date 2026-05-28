from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.workflows.models import Workflow


class WorkflowRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_in_workspace(
        self,
        workspace_id: UUID,
        *,
        page: int,
        page_size: int,
    ) -> tuple[list[Workflow], int]:
        """Paginated list of workflows in a workspace, newest first.

        Permission check (workspace membership) happens in the service
        layer — this method just runs the SQL.
        """

        offset = (page - 1) * page_size

        items_q = (
            select(Workflow)
            .where(
                Workflow.workspace_id == workspace_id,
                Workflow.deleted_at.is_(None),
            )
            .order_by(Workflow.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        total_q = select(func.count(Workflow.id)).where(
            Workflow.workspace_id == workspace_id,
            Workflow.deleted_at.is_(None),
        )

        items_result = await self.db.execute(items_q)
        items = list(items_result.scalars())
        total = (await self.db.execute(total_q)).scalar_one()
        return items, total

    async def get_in_workspace(
        self,
        workspace_id: UUID,
        workflow_id: UUID,
    ) -> Workflow | None:
        stmt = select(Workflow).where(
            Workflow.id == workflow_id,
            Workflow.workspace_id == workspace_id,
            Workflow.deleted_at.is_(None),
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def create(
        self,
        *,
        workspace_id: UUID,
        created_by: UUID,
        name: str,
        slug: str,
        description: str | None,
        graph_json: dict[str, Any],
        compiled_graph: dict[str, Any],
        settings: dict[str, Any] | None = None,
    ) -> Workflow:
        workflow = Workflow(
            workspace_id=workspace_id,
            created_by=created_by,
            name=name,
            slug=slug,
            description=description,
            status="draft",
            graph_json=graph_json,
            compiled_graph=compiled_graph,
            settings=settings or {},
        )
        self.db.add(workflow)
        await self.db.commit()
        await self.db.refresh(workflow)
        return workflow

    async def update(self, workflow: Workflow, **fields: Any) -> Workflow:
        for key, value in fields.items():
            setattr(workflow, key, value)
        await self.db.commit()
        await self.db.refresh(workflow)
        return workflow

    async def soft_delete(self, workflow: Workflow) -> None:
        workflow.deleted_at = datetime.now(UTC)
        await self.db.commit()
