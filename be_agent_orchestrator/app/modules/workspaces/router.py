from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status

from app.api.deps import get_current_user, get_workspace_service
from app.core.openapi import auth_required_responses
from app.core.schemas import PageResponse
from app.modules.users.models import User
from app.modules.workspaces.schemas import (
    CreateWorkspaceRequest,
    WorkspaceSummary,
)
from app.modules.workspaces.service import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get(
    "/",
    response_model=PageResponse[WorkspaceSummary],
    status_code=status.HTTP_200_OK,
    summary="List workspaces I belong to",
    description=(
        "Returns every workspace the authenticated user is a member of, "
        "with the user's role in each. Powers the landing-page workspace picker."
    ),
    operation_id="workspaces_get_list",
    responses=auth_required_responses(),
)
async def list_workspaces(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
) -> PageResponse[WorkspaceSummary]:
    items, total = await service.list_for_user(current_user.id, page=page, page_size=page_size)
    return PageResponse(items=items, total=total, page=page, page_size=page_size)


@router.post(
    "/",
    response_model=WorkspaceSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Create a workspace",
    description=(
        "Creates a workspace owned by the authenticated user. The caller is "
        "automatically added as a `workspace_members` row with role `owner`. "
        "Workspace `id` and `slug` are generated server-side."
    ),
    operation_id="workspaces_post_create",
    responses=auth_required_responses(),
)
async def create_workspace(
    payload: CreateWorkspaceRequest,
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
) -> WorkspaceSummary:
    return await service.create(owner_user_id=current_user.id, name=payload.name)


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a workspace",
    description=(
        "Marks the workspace as deleted (sets `deleted_at = now()`). "
        "The workspace immediately disappears from `GET /workspaces` and "
        "nested endpoints (workflows, agents, …) return 403 for it. "
        "**Only the workspace `owner` can delete.** "
        "Data is preserved on disk; recovery would be a future admin tool."
    ),
    operation_id="workspaces_delete",
    responses=auth_required_responses(404),
)
async def delete_workspace(
    workspace_id: UUID = Path(description="Workspace UUID."),
    current_user: User = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
) -> None:
    await service.delete(workspace_id, current_user.id)
