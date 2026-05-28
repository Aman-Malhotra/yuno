from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status

from app.api.deps import get_agent_service, get_current_user
from app.core.openapi import auth_required_responses
from app.core.schemas import PageResponse
from app.modules.agents.schemas import (
    AgentDetail,
    AgentSummary,
    CreateAgentRequest,
    UpdateAgentRequest,
)
from app.modules.agents.service import AgentService
from app.modules.users.models import User

router = APIRouter(prefix="/workspaces/{workspace_id}/agents", tags=["agents"])


@router.get(
    "/",
    response_model=PageResponse[AgentSummary],
    status_code=status.HTTP_200_OK,
    summary="List agents inside a workspace",
    description=(
        "Returns every agent in the workspace, newest first. "
        "Light shape: id, name, description, created_at, created_by. "
        "Use `GET /workspaces/{ws_id}/agents/{agent_id}` for the full config."
    ),
    operation_id="agents_get_list_in_workspace",
    responses=auth_required_responses(404),
)
async def list_agents_in_workspace(
    workspace_id: UUID = Path(description="Workspace UUID."),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: AgentService = Depends(get_agent_service),
) -> PageResponse[AgentSummary]:
    items, total = await service.list_in_workspace_for_user(
        workspace_id, current_user.id, page=page, page_size=page_size
    )
    return PageResponse(
        items=[AgentSummary.model_validate(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/",
    response_model=AgentDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create an agent in a workspace",
    description=(
        "Creates an agent (workflow node). The five mandatory fields are "
        "the minimum LangGraph needs to materialize the node at runtime via "
        "`create_react_agent(model, tools, prompt=...)`:\n\n"
        "- `name` — display name\n"
        "- `role` — short role label (used in conversation routing)\n"
        "- `system_prompt` — the LLM's system message\n"
        "- `model_provider` — LLM provider key (must be a configured one)\n"
        "- `model_name` — provider-specific model id\n\n"
        "All other fields (description, sampling params, memory/guardrails/limits/"
        "interaction-rules/skills configs) default to sensible values and can be "
        "edited later via the agent editor."
    ),
    operation_id="agents_post_create",
    responses=auth_required_responses(404, 422),
)
async def create_agent(
    payload: CreateAgentRequest,
    workspace_id: UUID = Path(description="Workspace UUID."),
    current_user: User = Depends(get_current_user),
    service: AgentService = Depends(get_agent_service),
) -> AgentDetail:
    agent = await service.create_in_workspace_for_user(workspace_id, current_user.id, payload)
    return AgentDetail.from_agent(agent)


@router.get(
    "/{agent_id}",
    response_model=AgentDetail,
    status_code=status.HTTP_200_OK,
    summary="Get an agent's full configuration",
    description=(
        "Returns every field needed to render the agent editor: prompt, "
        "model + sampling params, memory/schedule/guardrails/limits/skills "
        "configs (opaque JSONB), and audit fields."
    ),
    operation_id="agents_get_by_id",
    responses=auth_required_responses(404),
)
async def get_agent(
    workspace_id: UUID = Path(description="Workspace UUID."),
    agent_id: UUID = Path(description="Agent UUID."),
    current_user: User = Depends(get_current_user),
    service: AgentService = Depends(get_agent_service),
) -> AgentDetail:
    agent = await service.get_in_workspace_for_user(workspace_id, agent_id, current_user.id)
    return AgentDetail.from_agent(agent)


@router.patch(
    "/{agent_id}",
    response_model=AgentDetail,
    status_code=status.HTTP_200_OK,
    summary="Update an agent",
    description=(
        "Partial update — every field is optional. Omit a field to leave it "
        'unchanged. Pass `provider_credentials: {"api_key": "..."}` to '
        "rotate the BYOK key; pass `{}` to clear it (the agent will fall "
        "back to the user vault / server-level key at run time).\n\n"
        "Changing `model_provider` validates the new provider against the "
        "supported list. Key resolution is **not** re-checked here — the "
        "agent can sit in `draft` with no key until you actually run it."
    ),
    operation_id="agents_patch_update",
    responses=auth_required_responses(403, 404, 422),
)
async def update_agent(
    payload: UpdateAgentRequest,
    workspace_id: UUID = Path(description="Workspace UUID."),
    agent_id: UUID = Path(description="Agent UUID."),
    current_user: User = Depends(get_current_user),
    service: AgentService = Depends(get_agent_service),
) -> AgentDetail:
    agent = await service.update_in_workspace_for_user(
        workspace_id, agent_id, current_user.id, payload
    )
    return AgentDetail.from_agent(agent)
