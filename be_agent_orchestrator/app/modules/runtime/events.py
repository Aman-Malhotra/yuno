"""Per-run persistence helpers for ``workflow_run_nodes`` + ``runtime_events``.

The executor calls into a single ``RunPersistence`` instance for an entire
run. Sequence numbers are owned here (monotonic, scoped to the run) so
callers don't have to worry about ordering.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.runs.models import RuntimeEvent, WorkflowRun, WorkflowRunNode


class RunPersistence:
    def __init__(self, db: AsyncSession, run: WorkflowRun) -> None:
        self.db = db
        self.run = run
        self._seq = 0

    async def emit(
        self,
        event_type: str,
        *,
        node_id: str | None = None,
        run_node_id: UUID | None = None,
        agent_id: UUID | None = None,
        tool_id: UUID | None = None,
        message: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> RuntimeEvent:
        self._seq += 1
        event = RuntimeEvent(
            workspace_id=self.run.workspace_id,
            run_id=self.run.id,
            run_node_id=run_node_id,
            event_type=event_type,
            node_id=node_id,
            agent_id=agent_id,
            tool_id=tool_id,
            sequence_number=self._seq,
            message=message,
            payload=payload or {},
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def start_node(
        self,
        *,
        node_id: str,
        node_type: str,
        node_label: str | None,
        agent_id: UUID | None,
        tool_id: UUID | None,
        input_state: dict[str, Any],
    ) -> WorkflowRunNode:
        node_row = WorkflowRunNode(
            run_id=self.run.id,
            node_id=node_id,
            node_type=node_type,
            node_label=node_label,
            agent_id=agent_id,
            tool_id=tool_id,
            status="running",
            input=input_state,
            started_at=datetime.now(UTC),
        )
        self.db.add(node_row)
        await self.db.commit()
        await self.db.refresh(node_row)
        return node_row

    async def complete_node(
        self,
        node_row: WorkflowRunNode,
        *,
        status: str,
        output: dict[str, Any] | None = None,
        error_message: str | None = None,
        error_details: dict[str, Any] | None = None,
    ) -> None:
        node_row.status = status
        if output is not None:
            node_row.output = output
        if error_message is not None:
            node_row.error_message = error_message
        if error_details is not None:
            node_row.error_details = error_details
        node_row.completed_at = datetime.now(UTC)
        await self.db.commit()
