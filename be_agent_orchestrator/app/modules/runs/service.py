"""Workflow run lifecycle.

Today this only handles the *queue* half — creating a ``WorkflowRun`` row
and enqueuing the executor arq job. The job body itself is a stub that
will be filled in when the langgraph dispatcher lands. Splitting the
ingress from the executor lets us ship webhook plumbing end-to-end
(token → row → job) and test it with arq logs while the executor catches up.
"""

from typing import Any
from uuid import UUID

import structlog
from arq.connections import ArqRedis
from arq.jobs import Job

from app.core.errors import NotFoundError, ValidationError
from app.modules.runs.models import RuntimeEvent, WorkflowRun, WorkflowRunNode
from app.modules.runs.repository import RunRepository
from app.modules.workflows.models import Workflow
from app.modules.workspaces.service import WorkspaceService

log = structlog.get_logger("runs")

EXECUTE_JOB_NAME = "execute_workflow_run_job"

# Statuses that cannot be cancelled — the run is already finished.
TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


class RunService:
    def __init__(
        self,
        repository: RunRepository,
        arq_pool: ArqRedis,
        workspace_service: WorkspaceService,
    ) -> None:
        self.repository = repository
        self.arq_pool = arq_pool
        self.workspace_service = workspace_service

    # ──────────────────────────────────────────────────────────────────
    # Read
    # ──────────────────────────────────────────────────────────────────

    async def list_for_workspace(
        self,
        workspace_id: UUID,
        user_id: UUID,
        *,
        page: int,
        page_size: int,
        workflow_id: UUID | None,
        status: str | None,
    ) -> tuple[list[WorkflowRun], int]:
        await self.workspace_service.get_role_or_403(workspace_id, user_id)
        return await self.repository.list_in_workspace(
            workspace_id,
            page=page,
            page_size=page_size,
            workflow_id=workflow_id,
            status=status,
        )

    async def get_detail(
        self,
        workspace_id: UUID,
        run_id: UUID,
        user_id: UUID,
    ) -> tuple[WorkflowRun, list[WorkflowRunNode], list[RuntimeEvent]]:
        await self.workspace_service.get_role_or_403(workspace_id, user_id)
        run = await self.repository.get_in_workspace(workspace_id, run_id)
        if run is None:
            raise NotFoundError(
                "run_not_found",
                "Run does not exist in this workspace.",
                {"workspace_id": str(workspace_id), "run_id": str(run_id)},
            )
        nodes = await self.repository.list_nodes_for_run(run.id)
        events = await self.repository.list_events_for_run(run.id)
        return run, nodes, events

    # ──────────────────────────────────────────────────────────────────
    # Write
    # ──────────────────────────────────────────────────────────────────

    async def create_from_webhook(
        self,
        *,
        workflow: Workflow,
        input_state: dict[str, Any],
        trigger_source: str,
    ) -> WorkflowRun:
        """Queue a run kicked off by a webhook ingress.

        ``trigger_source`` is the webhook id (uuid string) so we can trace
        which token fired the run from the runs UI later.
        """

        if workflow.status == "archived":
            raise ValidationError(
                "workflow_archived",
                "Cannot trigger runs on an archived workflow.",
                {"workflow_id": str(workflow.id)},
            )

        run = await self.repository.create(
            workspace_id=workflow.workspace_id,
            workflow_id=workflow.id,
            trigger_type="api",
            trigger_source=trigger_source,
            triggered_by_user_id=None,
            input_state=input_state,
        )

        # Enqueue the executor. We pin the arq job_id to the run_id so the
        # cancel endpoint can call `abort_job(run_id)` without storing a
        # separate handle. (`_job_id` is arq's underscore-prefixed control
        # kwarg, distinct from the user-facing args passed to the function.)
        await self.arq_pool.enqueue_job(
            EXECUTE_JOB_NAME,
            run_id=str(run.id),
            workflow_id=str(workflow.id),
            _job_id=str(run.id),
        )

        log.info(
            "run.queued",
            run_id=str(run.id),
            workflow_id=str(workflow.id),
            trigger_type="api",
            trigger_source=trigger_source,
        )
        return run

    async def create_manual(
        self,
        *,
        workflow: Workflow,
        user_id: UUID,
        input_state: dict[str, Any],
    ) -> WorkflowRun:
        """Queue a manual / test run from inside the workspace UI.

        Distinct from ``create_from_webhook`` so the trigger_type column
        cleanly separates audience-facing executions from operator-driven
        smoke tests. The Runs/Logs/Costs UIs can filter on this.
        """

        if workflow.status == "archived":
            raise ValidationError(
                "workflow_archived",
                "Cannot trigger runs on an archived workflow.",
                {"workflow_id": str(workflow.id)},
            )

        run = await self.repository.create(
            workspace_id=workflow.workspace_id,
            workflow_id=workflow.id,
            trigger_type="test",
            trigger_source=f"user:{user_id}",
            triggered_by_user_id=user_id,
            input_state=input_state,
        )

        await self.arq_pool.enqueue_job(
            EXECUTE_JOB_NAME,
            run_id=str(run.id),
            workflow_id=str(workflow.id),
            _job_id=str(run.id),
        )

        log.info(
            "run.queued",
            run_id=str(run.id),
            workflow_id=str(workflow.id),
            trigger_type="test",
            triggered_by_user_id=str(user_id),
        )
        return run

    async def cancel(
        self,
        workspace_id: UUID,
        run_id: UUID,
        user_id: UUID,
    ) -> WorkflowRun:
        """Cancel a queued/running/waiting run.

        Calls ``arq.abort_job(run_id)`` which removes the job from the queue
        if it hasn't started yet, or asks a busy worker to abort it (arq
        raises ``asyncio.CancelledError`` inside the running job task; the
        executor's ``finally`` block flushes the cancelled state to DB).
        We also mark the run cancelled here so the UI flips immediately
        even if a worker hasn't yet acknowledged.
        """

        run = await self._get_or_404(workspace_id, run_id, user_id)
        if run.status in TERMINAL_STATUSES:
            raise ValidationError(
                "run_already_terminal",
                f"Run is already {run.status}; nothing to cancel.",
                {"run_id": str(run.id), "status": run.status},
            )

        # `Job.abort` writes `arq:abort:<job_id>` — the worker polls this
        # key. For queued jobs arq drops them; for in-flight jobs arq
        # cancels the task. Best-effort: if it fails (job already done,
        # redis hiccup) we still mark the row cancelled.
        try:
            await Job(job_id=str(run.id), redis=self.arq_pool).abort()
        except Exception as exc:  # noqa: BLE001
            log.warning("run.cancel.abort_failed", run_id=str(run.id), error=str(exc))

        run.status = "cancelled"
        await self.repository.db.commit()
        await self.repository.db.refresh(run)

        log.info(
            "run.cancelled",
            run_id=str(run.id),
            workspace_id=str(workspace_id),
            actor_user_id=str(user_id),
        )
        return run

    async def delete(
        self,
        workspace_id: UUID,
        run_id: UUID,
        user_id: UUID,
    ) -> None:
        """Hard delete a run and its children (nodes + events cascade).

        For an in-flight run we cancel first — otherwise the worker would
        still be writing back to a row that's about to disappear. Terminal
        runs are deleted straight through.
        """

        run = await self._get_or_404(workspace_id, run_id, user_id)
        if run.status not in TERMINAL_STATUSES:
            try:
                await Job(job_id=str(run.id), redis=self.arq_pool).abort()
            except Exception as exc:  # noqa: BLE001
                log.warning("run.delete.abort_failed", run_id=str(run.id), error=str(exc))

        await self.repository.delete(run)
        log.info(
            "run.deleted",
            run_id=str(run_id),
            workspace_id=str(workspace_id),
            actor_user_id=str(user_id),
        )

    async def _get_or_404(
        self,
        workspace_id: UUID,
        run_id: UUID,
        user_id: UUID,
    ) -> WorkflowRun:
        await self.workspace_service.get_role_or_403(workspace_id, user_id)
        run = await self.repository.get_in_workspace(workspace_id, run_id)
        if run is None:
            raise NotFoundError(
                "run_not_found",
                "Run does not exist in this workspace.",
                {"workspace_id": str(workspace_id), "run_id": str(run_id)},
            )
        return run
