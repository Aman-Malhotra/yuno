import re
import secrets
from uuid import UUID

import structlog

from app.core.errors import NotFoundError, ValidationError
from app.modules.agents.models import Agent
from app.modules.agents.repository import AgentRepository
from app.modules.agents.schemas import CreateAgentRequest, UpdateAgentRequest
from app.modules.llm.credentials_service import LLMCredentialsService
from app.modules.llm.factory import LLMFactory
from app.modules.llm.workspace_credentials_service import (
    WorkspaceLLMCredentialService,
)
from app.modules.workspaces.service import WorkspaceService

log = structlog.get_logger("agents")


def _slugify(text: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return base[:100] or "agent"


class AgentService:
    def __init__(
        self,
        repository: AgentRepository,
        workspace_service: WorkspaceService,
        # Vault service is still injected so the credentials router keeps
        # working (users can save keys for their own use), but it is NOT
        # consulted at agent execution time. The agent row's
        # ``provider_credentials.api_key`` is the only key the runtime
        # honors — by design.
        llm_credentials_service: LLMCredentialsService,
        # Workspace-default LLM credentials. Consulted at create time
        # (relaxes the BYOK requirement when a default exists) and at
        # run time (chain: agent BYOK → this → fail).
        workspace_llm_credentials_service: WorkspaceLLMCredentialService,
    ) -> None:
        self.repository = repository
        self.workspace_service = workspace_service
        self.llm_credentials_service = llm_credentials_service
        self.workspace_llm_credentials_service = workspace_llm_credentials_service

    async def list_in_workspace_for_user(
        self,
        workspace_id: UUID,
        user_id: UUID,
        *,
        page: int,
        page_size: int,
    ) -> tuple[list[Agent], int]:
        await self.workspace_service.get_role_or_403(workspace_id, user_id)
        return await self.repository.list_in_workspace(workspace_id, page=page, page_size=page_size)

    async def get_in_workspace_for_user(
        self,
        workspace_id: UUID,
        agent_id: UUID,
        user_id: UUID,
    ) -> Agent:
        await self.workspace_service.get_role_or_403(workspace_id, user_id)
        agent = await self.repository.get_in_workspace(workspace_id, agent_id)
        if agent is None:
            raise NotFoundError(
                "agent_not_found",
                "Agent does not exist in this workspace.",
                {"workspace_id": str(workspace_id), "agent_id": str(agent_id)},
            )
        return agent

    async def create_in_workspace_for_user(
        self,
        workspace_id: UUID,
        user_id: UUID,
        payload: CreateAgentRequest,
    ) -> Agent:
        """Create a workspace-scoped agent.

        Workspace membership is required (any role can create).

        Key rule: ``provider_credentials.api_key`` must be present on the
        request. We deliberately do not fall back to a user vault, a
        workspace vault, or a server env var — keys are scoped to the agent
        so a missing one always fails loudly at the right surface area.
        """

        await self.workspace_service.get_role_or_403(workspace_id, user_id)

        supported = LLMFactory.supported_providers()
        if payload.model_provider not in supported:
            raise ValidationError(
                "unsupported_model_provider",
                f"Unsupported model_provider {payload.model_provider!r}.",
                {"supported": supported},
            )

        provider_creds_dict: dict[str, str] = {}
        has_per_agent_key = False
        if payload.provider_credentials is not None:
            provider_creds_dict = payload.provider_credentials.model_dump(exclude_none=True)
            has_per_agent_key = bool(provider_creds_dict.get("api_key"))

        # Either the agent ships its own key, OR the workspace has a
        # default credential row for this provider that it can inherit
        # from at run time. If neither, fail loudly at the create surface.
        if not has_per_agent_key:
            workspace_key = await self.workspace_llm_credentials_service.resolve_api_key(
                workspace_id, payload.model_provider
            )
            if not workspace_key:
                raise ValidationError(
                    "provider_key_required",
                    f"No API key resolvable for provider {payload.model_provider!r}. "
                    "Either pass `provider_credentials.api_key` on this agent, "
                    "or configure a workspace-default credential at "
                    "`POST /workspaces/{workspace_id}/llm-providers/`.",
                    {"model_provider": payload.model_provider},
                )

        slug = f"{_slugify(payload.name)}-{secrets.token_hex(3)}"

        agent = await self.repository.create(
            workspace_id=workspace_id,
            created_by=user_id,
            name=payload.name,
            slug=slug,
            description=payload.description,
            role=payload.role,
            system_prompt=payload.system_prompt,
            model_provider=payload.model_provider,
            model_name=payload.model_name,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
            top_p=payload.top_p,
            memory_config=payload.memory_config,
            schedule_config=payload.schedule_config,
            guardrails_config=payload.guardrails_config,
            interaction_rules=payload.interaction_rules,
            limits_config=payload.limits_config,
            skills_config=payload.skills_config,
            provider_credentials=provider_creds_dict,
        )
        log.info(
            "agent.created",
            agent_id=str(agent.id),
            workspace_id=str(workspace_id),
            created_by=str(user_id),
            model_provider=agent.model_provider,
            model_name=agent.model_name,
        )
        return agent

    async def update_in_workspace_for_user(
        self,
        workspace_id: UUID,
        agent_id: UUID,
        user_id: UUID,
        payload: UpdateAgentRequest,
    ) -> Agent:
        """Partial-update an agent. Workspace membership required.

        If `model_provider` is changed, the new provider must be in the
        supported list. Key resolution (BYOK / vault / global) is *not*
        re-validated here — agents can sit in a `draft` state with no key,
        only the run-time dispatcher cares. Pass `provider_credentials`
        to rotate / clear the BYOK block in place.
        """

        agent = await self.get_in_workspace_for_user(workspace_id, agent_id, user_id)

        updates: dict[str, object] = {}

        if payload.name is not None:
            updates["name"] = payload.name
        if payload.role is not None:
            updates["role"] = payload.role
        if payload.system_prompt is not None:
            updates["system_prompt"] = payload.system_prompt
        if payload.description is not None:
            updates["description"] = payload.description
        if payload.status is not None:
            updates["status"] = payload.status

        if payload.model_provider is not None:
            supported = LLMFactory.supported_providers()
            if payload.model_provider not in supported:
                raise ValidationError(
                    "unsupported_model_provider",
                    f"Unsupported model_provider {payload.model_provider!r}.",
                    {"supported": supported},
                )
            updates["model_provider"] = payload.model_provider
        if payload.model_name is not None:
            updates["model_name"] = payload.model_name

        if payload.temperature is not None:
            updates["temperature"] = payload.temperature
        if payload.max_tokens is not None:
            updates["max_tokens"] = payload.max_tokens
        if payload.top_p is not None:
            updates["top_p"] = payload.top_p

        if payload.memory_config is not None:
            updates["memory_config"] = payload.memory_config
        if payload.schedule_config is not None:
            updates["schedule_config"] = payload.schedule_config
        if payload.guardrails_config is not None:
            updates["guardrails_config"] = payload.guardrails_config
        if payload.interaction_rules is not None:
            updates["interaction_rules"] = payload.interaction_rules
        if payload.limits_config is not None:
            updates["limits_config"] = payload.limits_config
        if payload.skills_config is not None:
            updates["skills_config"] = payload.skills_config

        if payload.provider_credentials is not None:
            updates["provider_credentials"] = payload.provider_credentials.model_dump(
                exclude_none=True
            )

        if not updates:
            return agent

        agent = await self.repository.update(agent, **updates)
        log.info(
            "agent.updated",
            agent_id=str(agent.id),
            workspace_id=str(workspace_id),
            actor_user_id=str(user_id),
            fields=list(updates),
        )
        return agent

    # ──────────────────────────────────────────────────────────────────
    # Runtime helper — used by the runtime executor to pick a key
    # ──────────────────────────────────────────────────────────────────

    async def resolve_api_key(self, agent: Agent) -> str | None:
        """Return the api_key to use for this agent's runs.

        Resolution chain (first hit wins):
          1. ``agent.provider_credentials.api_key`` (per-agent BYOK)
          2. Workspace-default credential for ``agent.model_provider``
          3. None — caller fails the node with a clear error

        No env fallback, no user vault. Keys are workspace-shared at most.
        """

        per_agent = (agent.provider_credentials or {}).get("api_key")
        if per_agent:
            return per_agent
        return await self.workspace_llm_credentials_service.resolve_api_key(
            agent.workspace_id, agent.model_provider
        )
