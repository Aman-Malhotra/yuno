from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.runs.models import RuntimeEvent, WorkflowRun, WorkflowRunNode


class RunRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        *,
        workspace_id: UUID,
        workflow_id: UUID,
        trigger_type: str,
        trigger_source: str | None,
        triggered_by_user_id: UUID | None,
        input_state: dict[str, Any],
    ) -> WorkflowRun:
        run = WorkflowRun(
            workspace_id=workspace_id,
            workflow_id=workflow_id,
            triggered_by_user_id=triggered_by_user_id,
            trigger_type=trigger_type,
            trigger_source=trigger_source,
            status="queued",
            input=input_state,
        )
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)
        return run

    async def list_in_workspace(
        self,
        workspace_id: UUID,
        *,
        page: int,
        page_size: int,
        workflow_id: UUID | None = None,
        status: str | None = None,
    ) -> tuple[list[WorkflowRun], int]:
        """Paginated runs, newest first. Optional filter by workflow + status."""

        offset = (page - 1) * page_size
        filters = [WorkflowRun.workspace_id == workspace_id]
        if workflow_id is not None:
            filters.append(WorkflowRun.workflow_id == workflow_id)
        if status is not None:
            filters.append(WorkflowRun.status == status)

        items_q = (
            select(WorkflowRun)
            .where(*filters)
            .order_by(WorkflowRun.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        total_q = select(func.count(WorkflowRun.id)).where(*filters)

        items = list((await self.db.execute(items_q)).scalars())
        total = (await self.db.execute(total_q)).scalar_one()
        return items, total

    async def get_in_workspace(
        self,
        workspace_id: UUID,
        run_id: UUID,
    ) -> WorkflowRun | None:
        stmt = select(WorkflowRun).where(
            WorkflowRun.id == run_id,
            WorkflowRun.workspace_id == workspace_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_nodes_for_run(self, run_id: UUID) -> list[WorkflowRunNode]:
        stmt = (
            select(WorkflowRunNode)
            .where(WorkflowRunNode.run_id == run_id)
            .order_by(WorkflowRunNode.started_at.nulls_last(), WorkflowRunNode.created_at)
        )
        return list((await self.db.execute(stmt)).scalars())

    async def list_events_for_run(
        self,
        run_id: UUID,
        *,
        limit: int = 500,
    ) -> list[RuntimeEvent]:
        stmt = (
            select(RuntimeEvent)
            .where(RuntimeEvent.run_id == run_id)
            .order_by(RuntimeEvent.sequence_number)
            .limit(limit)
        )
        return list((await self.db.execute(stmt)).scalars())

    async def delete(self, run: WorkflowRun) -> None:
        """Hard delete; ``workflow_run_nodes`` + ``runtime_events`` cascade via FK."""

        await self.db.delete(run)
        await self.db.commit()
