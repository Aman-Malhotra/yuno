from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Response, status

from app.api.deps import get_current_user, get_run_service
from app.core.openapi import auth_required_responses
from app.core.schemas import PageResponse
from app.modules.runs.schemas import (
    RunDetail,
    RunEventView,
    RunNodeView,
    RunStatus,
    RunSummary,
)
from app.modules.runs.service import RunService
from app.modules.users.models import User

router = APIRouter(prefix="/workspaces/{workspace_id}/runs", tags=["runs"])


@router.get(
    "/",
    response_model=PageResponse[RunSummary],
    status_code=status.HTTP_200_OK,
    summary="List workflow runs in a workspace",
    description=(
        "Paginated list of runs, newest first. Optionally filter by "
        "`workflow_id` and/or `status`. Returns the light shape — use "
        "`GET /workspaces/{ws}/runs/{run_id}` for per-step IO and the "
        "event stream."
    ),
    operation_id="runs_get_list_in_workspace",
    responses=auth_required_responses(404),
)
async def list_runs(
    workspace_id: UUID = Path(description="Workspace UUID."),
    workflow_id: UUID | None = Query(default=None, description="Filter by workflow."),
    status_filter: RunStatus | None = Query(
        default=None, alias="status", description="Filter by run status."
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: RunService = Depends(get_run_service),
) -> PageResponse[RunSummary]:
    items, total = await service.list_for_workspace(
        workspace_id,
        current_user.id,
        page=page,
        page_size=page_size,
        workflow_id=workflow_id,
        status=status_filter,
    )
    return PageResponse(
        items=[RunSummary.model_validate(r) for r in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{run_id}",
    response_model=RunDetail,
    status_code=status.HTTP_200_OK,
    summary="Get a run with per-step IO and the event stream",
    description=(
        "Returns the run row plus every `workflow_run_nodes` entry (per-step "
        "input/output/timing/error) and the first 500 `runtime_events` rows "
        "(timeline view). Use this on the run detail page."
    ),
    operation_id="runs_get_detail",
    responses=auth_required_responses(404),
)
async def get_run(
    workspace_id: UUID = Path(description="Workspace UUID."),
    run_id: UUID = Path(description="Run UUID."),
    current_user: User = Depends(get_current_user),
    service: RunService = Depends(get_run_service),
) -> RunDetail:
    run, nodes, events = await service.get_detail(workspace_id, run_id, current_user.id)
    return RunDetail(
        id=run.id,
        workspace_id=run.workspace_id,
        workflow_id=run.workflow_id,
        status=run.status,
        trigger_type=run.trigger_type,
        trigger_source=run.trigger_source,
        error_message=run.error_message,
        total_input_tokens=run.total_input_tokens,
        total_output_tokens=run.total_output_tokens,
        total_cost_usd=float(run.total_cost_usd),
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_at=run.created_at,
        updated_at=run.updated_at,
        input=run.input,
        output=run.output,
        nodes=[RunNodeView.model_validate(n) for n in nodes],
        events=[RunEventView.model_validate(e) for e in events],
    )


@router.post(
    "/{run_id}/cancel",
    response_model=RunSummary,
    status_code=status.HTTP_200_OK,
    summary="Cancel a queued or running workflow run",
    description=(
        "Marks the run `cancelled` and asks arq to abort the job. Queued "
        "jobs are removed from the queue before any work starts; running "
        "jobs receive a cancel signal — the executor's `finally` block is "
        "responsible for flushing state. Returns 422 if the run is already "
        "in a terminal state (`completed` / `failed` / `cancelled`)."
    ),
    operation_id="runs_post_cancel",
    responses=auth_required_responses(404, 422),
)
async def cancel_run(
    workspace_id: UUID = Path(description="Workspace UUID."),
    run_id: UUID = Path(description="Run UUID."),
    current_user: User = Depends(get_current_user),
    service: RunService = Depends(get_run_service),
) -> RunSummary:
    run = await service.cancel(workspace_id, run_id, current_user.id)
    return RunSummary.model_validate(run)


@router.delete(
    "/{run_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a run and its history",
    description=(
        "Hard delete — removes the run row plus all `workflow_run_nodes` "
        "and `runtime_events` (cascading FK). If the run is still "
        "queued/running, it is cancelled first so no worker writes back "
        "to a vanishing row."
    ),
    operation_id="runs_delete",
    responses=auth_required_responses(404),
)
async def delete_run(
    workspace_id: UUID = Path(description="Workspace UUID."),
    run_id: UUID = Path(description="Run UUID."),
    current_user: User = Depends(get_current_user),
    service: RunService = Depends(get_run_service),
) -> Response:
    await service.delete(workspace_id, run_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
