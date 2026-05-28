---
title: API Versioning and Router Composition
impact: CRITICAL
impactDescription: A single versioned mount point keeps the frontend contract stable as the API evolves
tags: api, routing, versioning
---

## API Versioning and Router Composition

All endpoints live under `/api/v1/...`. Routers **only compose** — they never hold business logic.

### Layout

```txt
app/api/
  deps.py            # shared dependencies
  router.py          # api_router → includes v1_router
  v1/
    router.py        # v1_router → includes each module router
    auth.py
    users.py
    agents.py
    workflows.py
    workflow_runs.py
    messages.py
    tools.py
    llm_providers.py
    channels.py
    monitoring.py
```

### Composition

```python
# app/api/router.py
from fastapi import APIRouter

from app.api.v1.router import router as v1_router

api_router = APIRouter()
api_router.include_router(v1_router, prefix="/v1")
```

```python
# app/api/v1/router.py
from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.agents.router import router as agents_router
from app.modules.workflows.router import router as workflows_router
from app.modules.runs.router import router as runs_router
from app.modules.messages.router import router as messages_router
from app.modules.tools.router import router as tools_router
from app.modules.llm.router import router as llm_router
from app.modules.channels.router import router as channels_router
from app.modules.monitoring.router import router as monitoring_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(agents_router)
router.include_router(workflows_router)
router.include_router(runs_router)
router.include_router(messages_router)
router.include_router(tools_router)
router.include_router(llm_router)
router.include_router(channels_router)
router.include_router(monitoring_router)
```

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.lifespan import lifespan


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
```

### Module router conventions

```python
# app/modules/agents/router.py
router = APIRouter(prefix="/agents", tags=["agents"])
```

- `prefix` set on the router, never hard-coded into paths
- `tags` set per module — drives the OpenAPI grouping
- Routes use plural nouns: `/agents`, `/workflows`, `/runs`, `/messages`

### Endpoint inventory (Yuno spec)

```txt
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout
GET    /api/v1/auth/me

GET    /api/v1/agents
POST   /api/v1/agents
GET    /api/v1/agents/{agent_id}
PATCH  /api/v1/agents/{agent_id}
DELETE /api/v1/agents/{agent_id}
POST   /api/v1/agents/{agent_id}/test

GET    /api/v1/workflows
POST   /api/v1/workflows
GET    /api/v1/workflows/{workflow_id}
PATCH  /api/v1/workflows/{workflow_id}
DELETE /api/v1/workflows/{workflow_id}
POST   /api/v1/workflows/{workflow_id}/validate
POST   /api/v1/workflows/{workflow_id}/run
GET    /api/v1/workflows/templates
POST   /api/v1/workflows/from-template/{template_id}

GET    /api/v1/runs
GET    /api/v1/runs/{run_id}
POST   /api/v1/runs/{run_id}/cancel
GET    /api/v1/runs/{run_id}/events
GET    /api/v1/runs/{run_id}/messages

GET    /api/v1/agents/{agent_id}/messages

GET    /api/v1/tools
POST   /api/v1/tools/{tool_id}/test

GET    /api/v1/llm-providers

GET    /api/v1/channels
POST   /api/v1/channels/telegram/connect
POST   /api/v1/channels/telegram/webhook
POST   /api/v1/channels/{channel_id}/disconnect

WS     /api/v1/monitoring/runs/{run_id}
```

### Bad — versionless paths

```python
# ❌ No version prefix — breaking changes will hurt
app.include_router(agents_router, prefix="/agents")
```

### Bad — routers holding logic

```python
# ❌ See arch-layering-separation
@router.get("/agents")
async def list_agents(db = Depends(get_db_session)):
    return (await db.execute(select(Agent))).scalars().all()
```

See: [[arch-layering-separation]], [[api-dependency-injection]], [[api-response-shapes]]
