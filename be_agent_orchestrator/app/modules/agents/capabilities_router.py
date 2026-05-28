"""Server-level agent-creation capabilities endpoint.

Two variants:
- ``GET /agents/capabilities`` — global; ``is_configured`` reflects per-user
  vault only. Kept for backwards-compat with the legacy FE form.
- ``GET /workspaces/{ws}/agents/capabilities`` — workspace-aware;
  ``is_configured`` ALSO flips when a workspace-default credential exists.
  New agent-create flow should call this one so users see their workspace
  defaults as pre-configured providers.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Path, status

from app.api.deps import (
    get_current_user,
    get_llm_credentials_service,
    get_workspace_llm_credentials_service,
)
from app.core.openapi import auth_required_responses
from app.modules.agents.capabilities import AgentCapabilities, build_capabilities
from app.modules.llm.credentials_service import LLMCredentialsService
from app.modules.llm.workspace_credentials_service import (
    WorkspaceLLMCredentialService,
)
from app.modules.users.models import User

router = APIRouter(prefix="/agents", tags=["agents"])
workspace_router = APIRouter(prefix="/workspaces/{workspace_id}/agents", tags=["agents"])


@router.get(
    "/capabilities",
    response_model=AgentCapabilities,
    status_code=status.HTTP_200_OK,
    summary="Get supported agent-creation configs",
    description=(
        "Returns everything the agent-builder UI needs to render the create-agent "
        "form without hard-coding anything:\n\n"
        "- `providers` — every LLM provider the server knows about, with a curated "
        "recommended-model list, the **per-user** `is_configured` flag (true iff "
        "either the server has a global key for it OR this user has saved one in "
        "their LLM credentials vault), and per-agent config fields with bounds.\n"
        "- `fields.mandatory` / `fields.optional` — every `CreateAgentRequest` field "
        "split by required-ness, with type/length/range constraints.\n"
        "- `tools` — built-in tools available to attach to agents (empty in v1 "
        "until the tool registry is wired).\n"
        "- `tool_entry_shape` — the expected shape of each item when attaching tools "
        "to an agent's `skills_config.tools` array.\n"
        "- `provider_credentials_shape` — schema for the optional per-agent BYOK "
        "field on agent creation."
    ),
    operation_id="agents_get_capabilities",
    responses=auth_required_responses(),
)
async def get_agent_capabilities(
    current_user: User = Depends(get_current_user),
    credentials_service: LLMCredentialsService = Depends(get_llm_credentials_service),
) -> AgentCapabilities:
    statuses = await credentials_service.list_for_user(current_user.id)
    user_keys = {s.provider for s in statuses if s.is_configured}
    return build_capabilities(user_provider_keys=user_keys)


@workspace_router.get(
    "/capabilities",
    response_model=AgentCapabilities,
    status_code=status.HTTP_200_OK,
    summary="Workspace-scoped agent-creation capabilities",
    description=(
        "Same shape as `GET /agents/capabilities` but `is_configured` also flips "
        "true for providers that have a workspace-default credential. Use this in "
        "the agent-create form so users can see which providers will fall back to "
        "the workspace's saved key without per-agent BYOK."
    ),
    operation_id="agents_get_capabilities_for_workspace",
    responses=auth_required_responses(404),
)
async def get_agent_capabilities_for_workspace(
    workspace_id: UUID = Path(description="Workspace UUID."),
    current_user: User = Depends(get_current_user),
    credentials_service: LLMCredentialsService = Depends(get_llm_credentials_service),
    workspace_credentials_service: WorkspaceLLMCredentialService = Depends(
        get_workspace_llm_credentials_service
    ),
) -> AgentCapabilities:
    statuses = await credentials_service.list_for_user(current_user.id)
    user_keys = {s.provider for s in statuses if s.is_configured}
    workspace_keys = await workspace_credentials_service.configured_providers(workspace_id)
    return build_capabilities(
        user_provider_keys=user_keys,
        workspace_provider_keys=workspace_keys,
    )
