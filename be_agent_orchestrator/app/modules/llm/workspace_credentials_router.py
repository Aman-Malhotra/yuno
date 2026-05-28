"""Workspace-scoped LLM provider credentials — CRUD endpoints.

Mounted at ``/workspaces/{workspace_id}/llm-providers``. Workspace
membership is required for every call (any role can manage credentials
for v1 — tighten to admin/owner later if needed).

Security note: the raw ``api_key`` is never returned by any endpoint.
The list / detail responses surface only ``last4`` so the UI can tell
multiple keys apart without leaking the secret. Same redaction rules as
the per-user vault apply in HTTP access logs.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Path, status

from app.api.deps import (
    get_current_user,
    get_workspace_llm_credentials_service,
)
from app.core.openapi import auth_required_responses
from app.modules.llm.workspace_credentials_schemas import (
    CreateWorkspaceCredentialRequest,
    UpdateWorkspaceCredentialRequest,
    WorkspaceCredentialListResponse,
    WorkspaceCredentialSummary,
)
from app.modules.llm.workspace_credentials_service import (
    WorkspaceLLMCredentialService,
)
from app.modules.users.models import User

router = APIRouter(
    prefix="/workspaces/{workspace_id}/llm-providers",
    tags=["workspace-llm-providers"],
)


@router.get(
    "/",
    response_model=WorkspaceCredentialListResponse,
    status_code=status.HTTP_200_OK,
    summary="List workspace-default LLM provider credentials",
    description=(
        "Returns every credential row attached to this workspace. The raw "
        "`api_key` is never echoed — only `last4` so the UI can tell multiple "
        "keys apart. Used by the agent-create form to populate the "
        '"use workspace default" dropdown.'
    ),
    operation_id="workspace_llm_providers_list",
    responses=auth_required_responses(404),
)
async def list_workspace_credentials(
    workspace_id: UUID = Path(description="Workspace UUID."),
    current_user: User = Depends(get_current_user),
    service: WorkspaceLLMCredentialService = Depends(get_workspace_llm_credentials_service),
) -> WorkspaceCredentialListResponse:
    items = await service.list_for_workspace(workspace_id, current_user.id)
    return WorkspaceCredentialListResponse(items=items)


@router.post(
    "/",
    response_model=WorkspaceCredentialSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Add or replace a workspace-default credential",
    description=(
        "Upserts the row for `(workspace, provider)`. Re-posting with the same "
        "provider overwrites the existing key — there's at most one row per "
        "provider per workspace."
    ),
    operation_id="workspace_llm_providers_create",
    responses=auth_required_responses(404, 422),
)
async def create_workspace_credential(
    payload: CreateWorkspaceCredentialRequest,
    workspace_id: UUID = Path(description="Workspace UUID."),
    current_user: User = Depends(get_current_user),
    service: WorkspaceLLMCredentialService = Depends(get_workspace_llm_credentials_service),
) -> WorkspaceCredentialSummary:
    return await service.create(workspace_id, current_user.id, payload)


@router.patch(
    "/{credential_id}",
    response_model=WorkspaceCredentialSummary,
    status_code=status.HTTP_200_OK,
    summary="Rotate / amend a workspace credential",
    description=(
        "Partial update — every field is optional. Pass `api_key` to rotate "
        'the secret in place; pass `base_url: ""` or `organization: ""` to '
        "clear those fields."
    ),
    operation_id="workspace_llm_providers_update",
    responses=auth_required_responses(404, 422),
)
async def update_workspace_credential(
    payload: UpdateWorkspaceCredentialRequest,
    workspace_id: UUID = Path(description="Workspace UUID."),
    credential_id: UUID = Path(description="Credential UUID."),
    current_user: User = Depends(get_current_user),
    service: WorkspaceLLMCredentialService = Depends(get_workspace_llm_credentials_service),
) -> WorkspaceCredentialSummary:
    return await service.update(workspace_id, credential_id, current_user.id, payload)


@router.delete(
    "/{credential_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a workspace credential",
    description=(
        "Removes the row. Agents using this provider but lacking their own "
        "BYOK key will start failing at the next run."
    ),
    operation_id="workspace_llm_providers_delete",
    responses=auth_required_responses(404),
)
async def delete_workspace_credential(
    workspace_id: UUID = Path(description="Workspace UUID."),
    credential_id: UUID = Path(description="Credential UUID."),
    current_user: User = Depends(get_current_user),
    service: WorkspaceLLMCredentialService = Depends(get_workspace_llm_credentials_service),
) -> None:
    await service.delete(workspace_id, credential_id, current_user.id)
