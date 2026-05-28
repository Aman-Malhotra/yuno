"""Arq job functions.

Each job opens its own DB session via ``AsyncSessionLocal`` — never put a
session on ``ctx``. Add new jobs here and wire them into
``WorkerSettings.functions`` in ``arq_app.py``.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.modules.agents.repository import AgentRepository
from app.modules.agents.service import AgentService
from app.modules.llm.credentials_repository import UserLLMCredentialRepository
from app.modules.llm.credentials_service import LLMCredentialsService
from app.modules.llm.workspace_credentials_repository import (
    WorkspaceLLMCredentialRepository,
)
from app.modules.llm.workspace_credentials_service import (
    WorkspaceLLMCredentialService,
)
from app.modules.memory.service import MemoryService
from app.modules.messages.repository import AgentMessageRepository
from app.modules.runs.models import WorkflowRun
from app.modules.runtime.executor import Executor, ExecutorError
from app.modules.tools.executor import ToolExecutor
from app.modules.tools.repository import ToolRepository
from app.modules.workflows.models import Workflow
from app.modules.workspaces.repository import WorkspaceRepository
from app.modules.workspaces.service import WorkspaceService

log = structlog.get_logger("worker")


async def execute_workflow_run_job(
    ctx: dict[str, Any],  # noqa: ARG001 — arq passes its own ctx, we ignore it
    *,
    run_id: str,
    workflow_id: str,
) -> dict[str, Any]:
    """Execute a queued workflow run.

    Walks ``workflow.compiled_graph`` via ``runtime.Executor``, persisting
    per-step IO + the event stream as it goes. Status transitions:

        queued → running → completed | failed | cancelled
    """

    log.info("run.execute.start", run_id=run_id, workflow_id=workflow_id)

    async with AsyncSessionLocal() as db:
        run = (
            await db.execute(select(WorkflowRun).where(WorkflowRun.id == UUID(run_id)))
        ).scalar_one_or_none()
        if run is None:
            log.warning("run.execute.missing", run_id=run_id)
            return {"status": "missing"}

        # Honor a cancel that landed between enqueue and pickup.
        if run.status == "cancelled":
            log.info("run.execute.skip_cancelled", run_id=run_id)
            return {"status": "cancelled"}

        workflow = (
            await db.execute(select(Workflow).where(Workflow.id == UUID(workflow_id)))
        ).scalar_one_or_none()
        if workflow is None:
            run.status = "failed"
            run.error_message = "workflow not found"
            run.completed_at = datetime.now(UTC)
            await db.commit()
            log.warning("run.execute.workflow_missing", run_id=run_id, workflow_id=workflow_id)
            return {"status": "failed", "error": "workflow_missing"}

        run.status = "running"
        run.started_at = datetime.now(UTC)
        await db.commit()

        # Dependency graph. The executor wants the agent + tool services
        # already resolved — assembled here per-job so each run gets its
        # own DB session and credential resolver.
        workspace_service = WorkspaceService(WorkspaceRepository(db))
        llm_credentials_service = LLMCredentialsService(UserLLMCredentialRepository(db))
        workspace_llm_credentials_service = WorkspaceLLMCredentialService(
            WorkspaceLLMCredentialRepository(db),
            workspace_service,
        )
        agent_service = AgentService(
            AgentRepository(db),
            workspace_service,
            llm_credentials_service,
            workspace_llm_credentials_service,
        )
        tool_repository = ToolRepository(db)
        tool_executor = ToolExecutor(tool_repository)
        message_repository = AgentMessageRepository(db)
        memory_service = MemoryService()

        executor = Executor(
            db,
            run,
            workflow,
            agent_service=agent_service,
            tool_executor=tool_executor,
            tool_repository=tool_repository,
            memory_service=memory_service,
            message_repository=message_repository,
        )

        try:
            await executor.run()
        except ExecutorError as err:
            run.status = "failed"
            run.error_message = f"executor: {err}"
            run.completed_at = datetime.now(UTC)
            await db.commit()
            log.warning("run.execute.executor_error", run_id=run_id, error=str(err))
            return {"status": "failed", "error": str(err)}
        except Exception as err:
            # Node-level failures already wrote status='failed' via
            # _record_failure; re-raise here is safe but we don't want it
            # to crash arq's retry path on a clean business-logic failure.
            log.exception("run.execute.unhandled", run_id=run_id)
            return {"status": "failed", "error": str(err)}

    log.info("run.execute.done", run_id=run_id, workflow_id=workflow_id)
    return {"status": run.status, "run_id": run_id}
