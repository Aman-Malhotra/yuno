from fastapi import APIRouter

from app.modules.agents.capabilities_router import (
    router as agents_capabilities_router,
)
from app.modules.agents.capabilities_router import (
    workspace_router as agents_capabilities_workspace_router,
)
from app.modules.agents.router import router as agents_router
from app.modules.auth.router import router as auth_router
from app.modules.channels.telegram_router import router as telegram_channel_router
from app.modules.llm.credentials_router import router as llm_credentials_router
from app.modules.llm.workspace_credentials_router import (
    router as workspace_llm_credentials_router,
)
from app.modules.memory.router import router as memory_router
from app.modules.runs.costs_router import router as costs_router
from app.modules.runs.router import router as runs_router
from app.modules.tools.router import router as tools_router
from app.modules.webhooks.ingress_router import router as webhooks_ingress_router
from app.modules.webhooks.router import router as webhooks_router
from app.modules.workflows.router import router as workflows_router
from app.modules.workspaces.router import router as workspaces_router

# Other module routers are mounted here as they come online:
# from app.modules.runs.router import router as runs_router
# from app.modules.messages.router import router as messages_router
# from app.modules.channels.router import router as channels_router
# from app.modules.monitoring.router import router as monitoring_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(workspaces_router)
router.include_router(workflows_router)
router.include_router(webhooks_router)
# Capabilities routers FIRST so their concrete paths
# (`/workspaces/{ws}/agents/capabilities`) win over `agents_router`'s
# `/workspaces/{ws}/agents/{agent_id}` — otherwise "capabilities" gets
# parsed as a UUID and the request 422s.
router.include_router(agents_capabilities_workspace_router)
router.include_router(agents_capabilities_router)
router.include_router(agents_router)
router.include_router(llm_credentials_router)
router.include_router(workspace_llm_credentials_router)
router.include_router(tools_router)
router.include_router(runs_router)
router.include_router(costs_router)
router.include_router(memory_router)
router.include_router(telegram_channel_router)

# Public webhook ingress — mounted last so the more specific
# /workspaces/{ws}/workflows/{wf}/webhooks/ routes take precedence over
# the catch-all /hooks/{workflow_id}/{token}.
router.include_router(webhooks_ingress_router)
# ...
