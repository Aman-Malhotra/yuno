from arq.connections import ArqRedis
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.agents.repository import AgentRepository
from app.modules.agents.service import AgentService
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.repository import RefreshTokenRepository
from app.modules.auth.service import AuthService
from app.modules.llm.credentials_repository import UserLLMCredentialRepository
from app.modules.llm.credentials_service import LLMCredentialsService
from app.modules.llm.workspace_credentials_repository import (
    WorkspaceLLMCredentialRepository,
)
from app.modules.llm.workspace_credentials_service import (
    WorkspaceLLMCredentialService,
)
from app.modules.runs.repository import RunRepository
from app.modules.runs.service import RunService
from app.modules.tools.executor import ToolExecutor
from app.modules.tools.repository import ToolRepository
from app.modules.tools.service import ToolService
from app.modules.users.repository import UserRepository
from app.modules.webhooks.repository import WebhookRepository
from app.modules.webhooks.service import WebhookService
from app.modules.workflows.repository import WorkflowRepository
from app.modules.workflows.service import WorkflowService
from app.modules.workspaces.repository import WorkspaceRepository
from app.modules.workspaces.service import WorkspaceService

__all__ = [
    "get_db_session",
    "get_arq_pool",
    "get_user_repository",
    "get_refresh_token_repository",
    "get_auth_service",
    "get_current_user",
    "get_workspace_repository",
    "get_workspace_service",
    "get_workflow_repository",
    "get_workflow_service",
    "get_agent_repository",
    "get_agent_service",
    "get_user_llm_credential_repository",
    "get_llm_credentials_service",
    "get_workspace_llm_credential_repository",
    "get_workspace_llm_credentials_service",
    "get_tool_repository",
    "get_tool_executor",
    "get_tool_service",
    "get_webhook_repository",
    "get_webhook_service",
    "get_run_repository",
    "get_run_service",
]


def get_arq_pool(request: Request) -> ArqRedis:
    return request.app.state.arq_pool  # type: ignore[no-any-return]


# ──────────────────────────────────────────────────────────────────────
# Auth wiring
# ──────────────────────────────────────────────────────────────────────


async def get_user_repository(
    db: AsyncSession = Depends(get_db_session),
) -> UserRepository:
    return UserRepository(db)


async def get_refresh_token_repository(
    db: AsyncSession = Depends(get_db_session),
) -> RefreshTokenRepository:
    return RefreshTokenRepository(db)


# ──────────────────────────────────────────────────────────────────────
# Workspaces
# ──────────────────────────────────────────────────────────────────────


async def get_workspace_repository(
    db: AsyncSession = Depends(get_db_session),
) -> WorkspaceRepository:
    return WorkspaceRepository(db)


async def get_workspace_service(
    repository: WorkspaceRepository = Depends(get_workspace_repository),
) -> WorkspaceService:
    return WorkspaceService(repository)


# ──────────────────────────────────────────────────────────────────────
# Workflows
# ──────────────────────────────────────────────────────────────────────


async def get_workflow_repository(
    db: AsyncSession = Depends(get_db_session),
) -> WorkflowRepository:
    return WorkflowRepository(db)


async def get_workflow_service(
    repository: WorkflowRepository = Depends(get_workflow_repository),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
) -> WorkflowService:
    return WorkflowService(repository, workspace_service)


# ──────────────────────────────────────────────────────────────────────
# LLM credentials (per-user vault)
# ──────────────────────────────────────────────────────────────────────


async def get_user_llm_credential_repository(
    db: AsyncSession = Depends(get_db_session),
) -> UserLLMCredentialRepository:
    return UserLLMCredentialRepository(db)


async def get_llm_credentials_service(
    repository: UserLLMCredentialRepository = Depends(get_user_llm_credential_repository),
) -> LLMCredentialsService:
    return LLMCredentialsService(repository)


# ──────────────────────────────────────────────────────────────────────
# Workspace-scoped LLM credentials (shared by every agent in the workspace)
# Declared BEFORE Agents so `get_agent_service` can reference the provider
# at module-load time — `Depends(...)` evaluates the callable at import.
# ──────────────────────────────────────────────────────────────────────


async def get_workspace_llm_credential_repository(
    db: AsyncSession = Depends(get_db_session),
) -> WorkspaceLLMCredentialRepository:
    return WorkspaceLLMCredentialRepository(db)


async def get_workspace_llm_credentials_service(
    repository: WorkspaceLLMCredentialRepository = Depends(get_workspace_llm_credential_repository),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
) -> WorkspaceLLMCredentialService:
    return WorkspaceLLMCredentialService(repository, workspace_service)


# ──────────────────────────────────────────────────────────────────────
# Agents
# ──────────────────────────────────────────────────────────────────────


async def get_agent_repository(
    db: AsyncSession = Depends(get_db_session),
) -> AgentRepository:
    return AgentRepository(db)


async def get_agent_service(
    repository: AgentRepository = Depends(get_agent_repository),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    llm_credentials_service: "LLMCredentialsService" = Depends(  # forward to avoid cycle order
        lambda db=Depends(get_db_session): LLMCredentialsService(UserLLMCredentialRepository(db))
    ),
    workspace_llm_credentials_service: WorkspaceLLMCredentialService = Depends(
        get_workspace_llm_credentials_service
    ),
) -> AgentService:
    return AgentService(
        repository,
        workspace_service,
        llm_credentials_service,
        workspace_llm_credentials_service,
    )


# ──────────────────────────────────────────────────────────────────────
# Tools
# ──────────────────────────────────────────────────────────────────────


async def get_tool_repository(
    db: AsyncSession = Depends(get_db_session),
) -> ToolRepository:
    return ToolRepository(db)


async def get_tool_executor(
    repository: ToolRepository = Depends(get_tool_repository),
) -> ToolExecutor:
    return ToolExecutor(repository)


async def get_tool_service(
    repository: ToolRepository = Depends(get_tool_repository),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    executor: ToolExecutor = Depends(get_tool_executor),
    agent_repository: AgentRepository = Depends(get_agent_repository),
) -> ToolService:
    return ToolService(repository, workspace_service, executor, agent_repository)


# ──────────────────────────────────────────────────────────────────────
# Webhooks
# ──────────────────────────────────────────────────────────────────────


async def get_webhook_repository(
    db: AsyncSession = Depends(get_db_session),
) -> WebhookRepository:
    return WebhookRepository(db)


async def get_webhook_service(
    repository: WebhookRepository = Depends(get_webhook_repository),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    workflow_service: WorkflowService = Depends(get_workflow_service),
) -> WebhookService:
    return WebhookService(repository, workspace_service, workflow_service)


# ──────────────────────────────────────────────────────────────────────
# Runs
# ──────────────────────────────────────────────────────────────────────


async def get_run_repository(
    db: AsyncSession = Depends(get_db_session),
) -> RunRepository:
    return RunRepository(db)


async def get_run_service(
    repository: RunRepository = Depends(get_run_repository),
    arq_pool: ArqRedis = Depends(get_arq_pool),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
) -> RunService:
    return RunService(repository, arq_pool, workspace_service)


# ──────────────────────────────────────────────────────────────────────
# Auth (depends on workspaces for personal-workspace provisioning on signup)
# ──────────────────────────────────────────────────────────────────────


async def get_auth_service(
    users: UserRepository = Depends(get_user_repository),
    tokens: RefreshTokenRepository = Depends(get_refresh_token_repository),
    workspaces: WorkspaceService = Depends(get_workspace_service),
) -> AuthService:
    return AuthService(users, tokens, workspaces)
