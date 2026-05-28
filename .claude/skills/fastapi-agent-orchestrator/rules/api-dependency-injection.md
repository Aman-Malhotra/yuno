---
title: FastAPI Dependencies, Not a DI Container
impact: CRITICAL
impactDescription: Keeps wiring explicit and obvious; avoids importing a heavy DI framework for no gain
tags: api, dependency-injection, fastapi
---

## FastAPI Dependencies, Not a DI Container

Use FastAPI's `Depends`. Do **not** pull in `dependency-injector`, `punq`, etc. The provider chain is small enough to write by hand.

### Standard wiring

```python
# app/api/deps.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session

from app.modules.agents.repository import AgentRepository
from app.modules.agents.service import AgentService

from app.modules.workflows.repository import WorkflowRepository
from app.modules.workflows.service import WorkflowService

from app.modules.runs.repository import RunRepository
from app.modules.runs.service import RunService


# Agents -----------------------------------------------------------------
async def get_agent_repository(
    db: AsyncSession = Depends(get_db_session),
) -> AgentRepository:
    return AgentRepository(db)


async def get_agent_service(
    repository: AgentRepository = Depends(get_agent_repository),
) -> AgentService:
    return AgentService(repository)


# Workflows --------------------------------------------------------------
async def get_workflow_repository(
    db: AsyncSession = Depends(get_db_session),
) -> WorkflowRepository:
    return WorkflowRepository(db)


async def get_workflow_service(
    repository: WorkflowRepository = Depends(get_workflow_repository),
    agent_service: AgentService = Depends(get_agent_service),
) -> WorkflowService:
    return WorkflowService(repository, agent_service)


# Runs -------------------------------------------------------------------
async def get_run_repository(
    db: AsyncSession = Depends(get_db_session),
) -> RunRepository:
    return RunRepository(db)


async def get_run_service(
    repository: RunRepository = Depends(get_run_repository),
    workflow_service: WorkflowService = Depends(get_workflow_service),
) -> RunService:
    return RunService(repository, workflow_service)
```

Routes pull only what they need:

```python
@router.post("/", response_model=AgentResponse, status_code=201)
async def create_agent(
    payload: CreateAgentRequest,
    current_user: User = Depends(get_current_user),
    service: AgentService = Depends(get_agent_service),
) -> AgentResponse:
    agent = await service.create_agent(user_id=current_user.id, payload=payload)
    return AgentResponse.model_validate(agent)
```

### Worker-side wiring

The worker doesn't have FastAPI's `Depends`. Construct services explicitly inside the job — use the same constructors.

```python
# app/worker/jobs.py
from app.db.session import AsyncSessionLocal
from app.modules.runs.repository import RunRepository
from app.modules.runs.service import RunService
from app.modules.runtime.langgraph_runtime import LangGraphRuntime


async def execute_workflow_job(ctx, run_id: str) -> None:
    async with AsyncSessionLocal() as db:
        run_service = RunService(RunRepository(db), ...)
        runtime = LangGraphRuntime(run_service, ctx["redis"])
        await runtime.execute_run(run_id)
```

### Bad — instantiating services inside routes

```python
# ❌ Repeats wiring; hard to override in tests
@router.post("/")
async def create_agent(payload: CreateAgentRequest, db = Depends(get_db_session)):
    service = AgentService(AgentRepository(db))
    return await service.create_agent(...)
```

### Bad — module-level singletons holding a session

```python
# ❌ Holds a session across requests — leaks, deadlocks
agent_service = AgentService(AgentRepository(SyncSession()))
```

### Test overrides

```python
# tests/conftest.py
app.dependency_overrides[get_db_session] = override_get_db_session
app.dependency_overrides[get_current_user] = override_current_user
```

### Rules

- One `Depends(...)` per provider; never call provider functions directly inside routes
- Services hold no global state — they take repositories (and other services) as constructor args
- Repositories take an `AsyncSession` as a constructor arg — never store one as a module global
- No third-party DI containers

See: [[arch-layering-separation]], [[db-session-lifecycle]], [[auth-current-user-dep]]
