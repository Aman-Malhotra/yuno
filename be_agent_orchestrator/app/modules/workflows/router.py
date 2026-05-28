from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Query, Response, status

from app.api.deps import (
    get_current_user,
    get_run_service,
    get_workflow_service,
)
from app.core.openapi import auth_required_responses
from app.core.schemas import PageResponse
from app.modules.runs.schemas import RunSummary
from app.modules.runs.service import RunService
from app.modules.users.models import User
from app.modules.workflows.schemas import (
    CreateWorkflowRequest,
    UpdateWorkflowGraphRequest,
    UpdateWorkflowRequest,
    WorkflowDetail,
    WorkflowSummary,
)
from app.modules.workflows.service import WorkflowService

router = APIRouter(prefix="/workspaces/{workspace_id}/workflows", tags=["workflows"])


@router.get(
    "/",
    response_model=PageResponse[WorkflowSummary],
    status_code=status.HTTP_200_OK,
    summary="List workflows inside a workspace",
    description=(
        "Returns every workflow in the given workspace, newest first. "
        "The caller must be a member of the workspace (any role)."
    ),
    operation_id="workflows_get_list_in_workspace",
    responses=auth_required_responses(404),
)
async def list_workflows_in_workspace(
    workspace_id: UUID = Path(description="Workspace UUID."),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: WorkflowService = Depends(get_workflow_service),
) -> PageResponse[WorkflowSummary]:
    items, total = await service.list_in_workspace_for_user(
        workspace_id, current_user.id, page=page, page_size=page_size
    )
    return PageResponse(
        items=[WorkflowSummary.model_validate(w) for w in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/",
    response_model=WorkflowDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create a workflow in a workspace",
    description=(
        "Creates a workflow. The `graph` field is optional — when omitted, "
        "the canvas is seeded with a single `start` node so the builder has "
        "an anchor to wire from.\n\n"
        "Agent ids referenced by `agent` nodes (if any) must already exist "
        "in this workspace. Structural checks (start/end presence, no "
        "orphans) are **not** enforced here — only on transition to "
        "`published` via PATCH."
    ),
    operation_id="workflows_post_create",
    responses=auth_required_responses(404, 422),
)
async def create_workflow(
    payload: CreateWorkflowRequest,
    workspace_id: UUID = Path(description="Workspace UUID."),
    current_user: User = Depends(get_current_user),
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowDetail:
    workflow = await service.create_in_workspace_for_user(workspace_id, current_user.id, payload)
    return WorkflowDetail.from_workflow(workflow)


@router.get(
    "/{workflow_id}",
    response_model=WorkflowDetail,
    status_code=status.HTTP_200_OK,
    summary="Get a workflow with its full graph",
    description=(
        "Returns the workflow including `graph` (React Flow shape) and "
        "`compiled_graph` (langgraph-ready normalized shape). The builder "
        "uses `graph`; the runtime dispatcher reads `compiled_graph`."
    ),
    operation_id="workflows_get_by_id",
    responses=auth_required_responses(404),
)
async def get_workflow(
    workspace_id: UUID = Path(description="Workspace UUID."),
    workflow_id: UUID = Path(description="Workflow UUID."),
    current_user: User = Depends(get_current_user),
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowDetail:
    workflow = await service.get_in_workspace_for_user(workspace_id, workflow_id, current_user.id)
    return WorkflowDetail.from_workflow(workflow)


@router.patch(
    "/{workflow_id}",
    response_model=WorkflowDetail,
    status_code=status.HTTP_200_OK,
    summary="Update workflow metadata",
    description=(
        "Partial update of metadata: `name`, `description`, `status`, "
        "`settings`. The graph itself is updated via "
        "`PATCH /workspaces/{ws}/workflows/{id}/graph` so autosave from "
        "the canvas can stay cheap.\n\n"
        "Setting `status` to `published` runs strict structural checks "
        "on the current graph and 422s with `issues` if anything is wrong."
    ),
    operation_id="workflows_patch_update",
    responses=auth_required_responses(404, 422),
)
async def update_workflow(
    payload: UpdateWorkflowRequest,
    workspace_id: UUID = Path(description="Workspace UUID."),
    workflow_id: UUID = Path(description="Workflow UUID."),
    current_user: User = Depends(get_current_user),
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowDetail:
    workflow = await service.update_in_workspace_for_user(
        workspace_id, workflow_id, current_user.id, payload
    )
    return WorkflowDetail.from_workflow(workflow)


@router.patch(
    "/{workflow_id}/graph",
    response_model=WorkflowDetail,
    status_code=status.HTTP_200_OK,
    summary="Replace the workflow's graph (autosave)",
    description=(
        "Dedicated PATCH for the React Flow canvas autosave. Replaces "
        "`graph_json` wholesale and re-derives `compiled_graph` "
        "(langgraph-ready normalization with `add_conditional_edges` "
        "grouping). Agent refs are validated against this workspace; "
        "in-progress graphs (missing end node, agent nodes without an "
        "`agentId`) are tolerated."
    ),
    operation_id="workflows_patch_graph",
    responses=auth_required_responses(404, 422),
)
async def update_workflow_graph(
    payload: UpdateWorkflowGraphRequest,
    workspace_id: UUID = Path(description="Workspace UUID."),
    workflow_id: UUID = Path(description="Workflow UUID."),
    current_user: User = Depends(get_current_user),
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowDetail:
    workflow = await service.update_graph_in_workspace_for_user(
        workspace_id, workflow_id, current_user.id, payload
    )
    return WorkflowDetail.from_workflow(workflow)


@router.delete(
    "/{workflow_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a workflow",
    description="Marks the workflow as deleted. Idempotent — already-deleted workflows return 404.",
    operation_id="workflows_delete",
    responses=auth_required_responses(404),
)
async def delete_workflow(
    workspace_id: UUID = Path(description="Workspace UUID."),
    workflow_id: UUID = Path(description="Workflow UUID."),
    current_user: User = Depends(get_current_user),
    service: WorkflowService = Depends(get_workflow_service),
) -> Response:
    await service.soft_delete_in_workspace_for_user(workspace_id, workflow_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ──────────────────────────────────────────────────────────────────────
# Manual / test run trigger
# ──────────────────────────────────────────────────────────────────────


@router.post(
    "/{workflow_id}/runs",
    response_model=RunSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger a manual / test run of this workflow",
    description=(
        "Queues a workflow run with caller-supplied initial state. Stamped "
        "with `trigger_type='test'` so the Runs / Logs / Costs UIs can "
        "separate operator smoke-tests from real channel-driven traffic.\n\n"
        "The request body is an opaque JSON object — every key becomes "
        "available to the executor as `state.<key>`. The workflow's first "
        "agent should read the same fields its production trigger would."
    ),
    operation_id="workflows_post_manual_run",
    responses=auth_required_responses(404, 422),
)
async def trigger_manual_run(
    workspace_id: UUID = Path(description="Workspace UUID."),
    workflow_id: UUID = Path(description="Workflow UUID."),
    input_state: dict[str, Any] = Body(
        default_factory=dict,
        description=(
            "Initial run state. Provide whatever shape the workflow's first "
            "agent expects (e.g. `{\"message\": \"...\", \"chat_id\": 123}`)."
        ),
    ),
    current_user: User = Depends(get_current_user),
    workflow_service: WorkflowService = Depends(get_workflow_service),
    run_service: RunService = Depends(get_run_service),
) -> RunSummary:
    # `get_in_workspace_for_user` handles both workspace-membership 403
    # and not-found 404 for us — no extra guard needed.
    workflow = await workflow_service.get_in_workspace_for_user(
        workspace_id, workflow_id, current_user.id
    )
    run = await run_service.create_manual(
        workflow=workflow,
        user_id=current_user.id,
        input_state=input_state or {},
    )
    return RunSummary.model_validate(run)
