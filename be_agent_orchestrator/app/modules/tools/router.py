"""HTTP routes for the tool registry."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status

from app.api.deps import get_current_user, get_tool_service
from app.core.openapi import auth_required_responses
from app.core.schemas import PageResponse
from app.modules.tools.builtins import list_builtins
from app.modules.tools.schemas import (
    AgentToolDetail,
    ApprovalDecisionRequest,
    AttachToolRequest,
    CreateToolRequest,
    ExecuteToolRequest,
    ToolApprovalDetail,
    ToolDetail,
    ToolExecutionDetail,
    ToolExecutionLogEntry,
    ToolSummary,
    ToolVersionSummary,
    UpdateToolRequest,
)
from app.modules.tools.service import ToolService
from app.modules.users.models import User

router = APIRouter(prefix="/workspaces/{workspace_id}/tools", tags=["tools"])


# ──────────────────────────────────────────────────────────────────────
# Discovery
# ──────────────────────────────────────────────────────────────────────


@router.get(
    "/builtins",
    response_model=list[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="List all registered built-in tool handlers",
    description=(
        "Built-ins are the handlers compiled into the platform "
        "(calculator, web_search, ask_agent, …). Use this endpoint to "
        "populate the tool-creation UI's `handler` picker for `type=builtin` "
        "tools."
    ),
    operation_id="tools_get_builtin_registry",
    responses=auth_required_responses(),
)
async def list_builtin_handlers(
    _workspace_id: UUID = Path(alias="workspace_id"),
    _current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    return [
        {
            "name": spec.name,
            "description": spec.description,
            "category": spec.category,
            "input_schema": spec.input_schema,
            "output_schema": spec.output_schema,
        }
        for spec in list_builtins()
    ]


# ──────────────────────────────────────────────────────────────────────
# Tools — CRUD
# ──────────────────────────────────────────────────────────────────────


@router.get(
    "/",
    response_model=PageResponse[ToolSummary],
    status_code=status.HTTP_200_OK,
    summary="List tools in a workspace",
    description=(
        "Workspace-scoped tools plus global built-ins, newest first. Filter "
        "with `type=`, `category=`, `status=`."
    ),
    operation_id="tools_get_list_in_workspace",
    responses=auth_required_responses(404),
)
async def list_tools(
    workspace_id: UUID = Path(),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type_filter: str | None = Query(None, alias="type"),
    category: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    service: ToolService = Depends(get_tool_service),
) -> PageResponse[ToolSummary]:
    items, total = await service.list_in_workspace(
        workspace_id,
        current_user.id,
        page=page,
        page_size=page_size,
        type_filter=type_filter,
        category=category,
        status_filter=status_filter,
    )
    return PageResponse(
        items=[ToolSummary.model_validate(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/",
    response_model=ToolDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create a tool in a workspace",
    description=(
        "Creates a workspace-scoped tool. Required: `name`, `description`, "
        "`type`. Most useful for `type=http` (REST integrations) and `type=builtin` "
        "(register a registered handler). Returns the full ToolDetail; a `v1` "
        "snapshot is created on the side and visible via `GET .../versions`."
    ),
    operation_id="tools_post_create",
    responses=auth_required_responses(404, 409, 422),
)
async def create_tool(
    payload: CreateToolRequest,
    workspace_id: UUID = Path(),
    current_user: User = Depends(get_current_user),
    service: ToolService = Depends(get_tool_service),
) -> ToolDetail:
    tool = await service.create(workspace_id, current_user.id, payload)
    return ToolDetail.from_orm(tool)


@router.get(
    "/{tool_id}",
    response_model=ToolDetail,
    status_code=status.HTTP_200_OK,
    summary="Get a tool's full definition",
    operation_id="tools_get_by_id",
    responses=auth_required_responses(404),
)
async def get_tool(
    workspace_id: UUID = Path(),
    tool_id: UUID = Path(),
    current_user: User = Depends(get_current_user),
    service: ToolService = Depends(get_tool_service),
) -> ToolDetail:
    tool = await service.get_in_workspace(workspace_id, tool_id, current_user.id)
    return ToolDetail.from_orm(tool)


@router.patch(
    "/{tool_id}",
    response_model=ToolDetail,
    status_code=status.HTTP_200_OK,
    summary="Update a tool",
    description=(
        "Partial update. Pass `publish_new_version: true` to snapshot the "
        "result so workflow runs pinned to the older version keep using its "
        "schema and config."
    ),
    operation_id="tools_patch_update",
    responses=auth_required_responses(403, 404, 422),
)
async def update_tool(
    payload: UpdateToolRequest,
    workspace_id: UUID = Path(),
    tool_id: UUID = Path(),
    current_user: User = Depends(get_current_user),
    service: ToolService = Depends(get_tool_service),
) -> ToolDetail:
    tool = await service.update(workspace_id, tool_id, current_user.id, payload)
    return ToolDetail.from_orm(tool)


@router.delete(
    "/{tool_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a tool",
    operation_id="tools_delete",
    responses=auth_required_responses(403, 404),
)
async def delete_tool(
    workspace_id: UUID = Path(),
    tool_id: UUID = Path(),
    current_user: User = Depends(get_current_user),
    service: ToolService = Depends(get_tool_service),
) -> None:
    await service.delete(workspace_id, tool_id, current_user.id)


# ──────────────────────────────────────────────────────────────────────
# Versions
# ──────────────────────────────────────────────────────────────────────


@router.get(
    "/{tool_id}/versions",
    response_model=list[ToolVersionSummary],
    status_code=status.HTTP_200_OK,
    summary="List published versions of a tool",
    operation_id="tools_get_versions",
    responses=auth_required_responses(404),
)
async def list_tool_versions(
    workspace_id: UUID = Path(),
    tool_id: UUID = Path(),
    current_user: User = Depends(get_current_user),
    service: ToolService = Depends(get_tool_service),
) -> list[ToolVersionSummary]:
    versions = await service.list_versions(workspace_id, tool_id, current_user.id)
    return [ToolVersionSummary.model_validate(v) for v in versions]


# ──────────────────────────────────────────────────────────────────────
# Test console
# ──────────────────────────────────────────────────────────────────────


@router.post(
    "/{tool_id}/test",
    response_model=ToolExecutionDetail,
    status_code=status.HTTP_200_OK,
    summary="Run a tool with synthetic input (test console)",
    description=(
        "Dispatches the tool synchronously and returns a fully-resolved "
        "`ToolExecutionDetail` (status, output, logs, duration). Pass "
        "`dry_run: true` to render the resolved request payload without "
        "actually calling the backend — useful for inspecting templating."
    ),
    operation_id="tools_post_test_run",
    responses=auth_required_responses(404, 422),
)
async def test_tool(
    payload: ExecuteToolRequest,
    workspace_id: UUID = Path(),
    tool_id: UUID = Path(),
    current_user: User = Depends(get_current_user),
    service: ToolService = Depends(get_tool_service),
) -> ToolExecutionDetail:
    result = await service.execute_for_test(workspace_id, tool_id, current_user.id, payload)
    # Dry-run/transient mode returns a plain envelope, not a row.
    if isinstance(result, dict):
        return _envelope_to_execution_detail(result, tool_id=tool_id)
    logs = await service.repository.list_logs(result.id)
    return _execution_to_detail(result, logs)


# ──────────────────────────────────────────────────────────────────────
# Executions
# ──────────────────────────────────────────────────────────────────────


@router.get(
    "/{tool_id}/executions",
    response_model=PageResponse[ToolExecutionDetail],
    status_code=status.HTTP_200_OK,
    summary="List executions of a tool",
    operation_id="tools_get_executions",
    responses=auth_required_responses(404),
)
async def list_tool_executions(
    workspace_id: UUID = Path(),
    tool_id: UUID = Path(),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: ToolService = Depends(get_tool_service),
) -> PageResponse[ToolExecutionDetail]:
    items, total = await service.list_executions(
        workspace_id, tool_id, current_user.id, page=page, page_size=page_size
    )
    return PageResponse(
        items=[_execution_to_detail(e, logs=[]) for e in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/executions/{execution_id}",
    response_model=ToolExecutionDetail,
    status_code=status.HTTP_200_OK,
    summary="Get a single tool execution + its log stream",
    operation_id="tools_get_execution_by_id",
    responses=auth_required_responses(404),
)
async def get_tool_execution(
    workspace_id: UUID = Path(),
    execution_id: UUID = Path(),
    current_user: User = Depends(get_current_user),
    service: ToolService = Depends(get_tool_service),
) -> ToolExecutionDetail:
    execution, logs = await service.get_execution(workspace_id, execution_id, current_user.id)
    return _execution_to_detail(execution, logs)


# ──────────────────────────────────────────────────────────────────────
# Approvals
# ──────────────────────────────────────────────────────────────────────


@router.get(
    "/approvals/pending",
    response_model=list[ToolApprovalDetail],
    status_code=status.HTTP_200_OK,
    summary="List tool executions waiting on human approval",
    operation_id="tools_get_pending_approvals",
    responses=auth_required_responses(404),
)
async def list_pending_approvals(
    workspace_id: UUID = Path(),
    current_user: User = Depends(get_current_user),
    service: ToolService = Depends(get_tool_service),
) -> list[ToolApprovalDetail]:
    approvals = await service.list_pending_approvals(workspace_id, current_user.id)
    return [ToolApprovalDetail.model_validate(a) for a in approvals]


@router.post(
    "/approvals/{approval_id}/decision",
    response_model=ToolApprovalDetail,
    status_code=status.HTTP_200_OK,
    summary="Approve or reject a pending tool execution",
    operation_id="tools_post_approval_decision",
    responses=auth_required_responses(404, 409, 422),
)
async def decide_approval(
    payload: ApprovalDecisionRequest,
    workspace_id: UUID = Path(),
    approval_id: UUID = Path(),
    current_user: User = Depends(get_current_user),
    service: ToolService = Depends(get_tool_service),
) -> ToolApprovalDetail:
    approval = await service.decide_approval(
        workspace_id,
        approval_id,
        current_user.id,
        decision=payload.decision,
        reason=payload.reason,
    )
    return ToolApprovalDetail.model_validate(approval)


# ──────────────────────────────────────────────────────────────────────
# Agent ↔ Tool permissions
# ──────────────────────────────────────────────────────────────────────


@router.get(
    "/agents/{agent_id}/permissions",
    response_model=list[AgentToolDetail],
    status_code=status.HTTP_200_OK,
    summary="List tools attached to an agent",
    operation_id="tools_get_agent_permissions",
    responses=auth_required_responses(404),
)
async def list_agent_permissions(
    workspace_id: UUID = Path(),
    agent_id: UUID = Path(),
    current_user: User = Depends(get_current_user),
    service: ToolService = Depends(get_tool_service),
) -> list[AgentToolDetail]:
    links = await service.list_agent_tools(workspace_id, agent_id, current_user.id)
    return [
        AgentToolDetail(
            id=link.id,
            agent_id=link.agent_id,
            tool_id=link.tool_id,
            is_enabled=link.is_enabled,
            permission=ToolService.agent_tool_permission(link),
            created_at=link.created_at,
        )
        for link in links
    ]


@router.post(
    "/agents/{agent_id}/permissions",
    response_model=AgentToolDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Attach a tool to an agent",
    description=(
        "Grants the agent the right to call `tool_id` during a run. Use the "
        "`permission` object to require human approval, cap calls per run, or "
        "stamp default input values."
    ),
    operation_id="tools_post_agent_permission",
    responses=auth_required_responses(404, 409, 422),
)
async def attach_tool_to_agent(
    payload: AttachToolRequest,
    workspace_id: UUID = Path(),
    agent_id: UUID = Path(),
    current_user: User = Depends(get_current_user),
    service: ToolService = Depends(get_tool_service),
) -> AgentToolDetail:
    link = await service.attach_tool(workspace_id, agent_id, current_user.id, payload)
    return AgentToolDetail(
        id=link.id,
        agent_id=link.agent_id,
        tool_id=link.tool_id,
        is_enabled=link.is_enabled,
        permission=ToolService.agent_tool_permission(link),
        created_at=link.created_at,
    )


@router.delete(
    "/agents/{agent_id}/permissions/{tool_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Detach a tool from an agent",
    operation_id="tools_delete_agent_permission",
    responses=auth_required_responses(404),
)
async def detach_tool_from_agent(
    workspace_id: UUID = Path(),
    agent_id: UUID = Path(),
    tool_id: UUID = Path(),
    current_user: User = Depends(get_current_user),
    service: ToolService = Depends(get_tool_service),
) -> None:
    await service.detach_tool(workspace_id, agent_id, tool_id, current_user.id)


# ──────────────────────────────────────────────────────────────────────
# Helpers — ORM → response mapping
# ──────────────────────────────────────────────────────────────────────


def _execution_to_detail(execution: Any, logs: list[Any]) -> ToolExecutionDetail:
    return ToolExecutionDetail(
        id=execution.id,
        tool_id=execution.tool_id,
        tool_name=execution.tool_name,
        tool_version=execution.tool_version,
        agent_id=execution.agent_id,
        run_id=execution.run_id,
        status=execution.status,
        input=execution.input or {},
        output=execution.output or {},
        error_message=execution.error_message,
        error_details=execution.error_details or {},
        duration_ms=execution.duration_ms,
        retry_count=execution.retry_count,
        tokens_used=execution.tokens_used,
        cost_usd=float(execution.cost_usd) if execution.cost_usd is not None else None,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        created_at=execution.created_at,
        logs=[
            ToolExecutionLogEntry(
                id=log.id,
                level=log.level,
                message=log.message,
                metadata=log.log_metadata or {},
                created_at=log.created_at,
            )
            for log in logs
        ],
    )


def _envelope_to_execution_detail(
    envelope: dict[str, Any], *, tool_id: UUID
) -> ToolExecutionDetail:
    """Synthesize a ToolExecutionDetail for transient (dry-run) results."""

    from datetime import UTC, datetime
    from uuid import uuid4

    now = datetime.now(UTC)
    return ToolExecutionDetail(
        id=uuid4(),
        tool_id=tool_id,
        tool_name="(dry-run)",
        tool_version=0,
        agent_id=None,
        run_id=None,
        status="success" if envelope.get("success") else "failed",
        input={},
        output=envelope,
        error_message=envelope.get("error"),
        error_details={},
        duration_ms=envelope.get("duration_ms"),
        retry_count=envelope.get("retries") or 0,
        tokens_used=None,
        cost_usd=None,
        started_at=now,
        completed_at=now,
        created_at=now,
        logs=[],
    )
