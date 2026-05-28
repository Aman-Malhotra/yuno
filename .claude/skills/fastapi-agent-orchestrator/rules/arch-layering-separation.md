---
title: API → Service → Repository Layering
impact: CRITICAL
impactDescription: Keeps HTTP concerns, business logic, and DB queries from bleeding into each other — the spec explicitly grades for "clear separation"
tags: architecture, layering, separation-of-concerns
---

## API → Service → Repository Layering

Every request flows through three layers, in order. Never skip one.

```txt
Router (HTTP)   ──►  Service (business logic, permissions, orchestration)  ──►  Repository (DB only)
```

| Layer       | May do                                              | May NOT do                                          |
|-------------|-----------------------------------------------------|-----------------------------------------------------|
| Router      | Parse request, call service, return response        | DB queries, business rules, calling other services  |
| Service     | Business rules, permission checks, call repos, enqueue jobs, emit events | Build HTTP responses, raise `HTTPException` directly |
| Repository  | `select`, `insert`, `update`, `delete`, joins       | Business rules, permission checks, HTTP, queueing   |

### Bad — router doing DB queries

```python
# ❌ Router holds DB logic + business rules
@router.post("/agents")
async def create_agent(payload: CreateAgentRequest, db: AsyncSession = Depends(get_db_session)):
    if not payload.name:
        raise HTTPException(400, "name required")
    agent = Agent(**payload.model_dump())
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent
```

### Bad — service raising HTTP errors

```python
# ❌ Service knows it's behind HTTP — couples it to FastAPI
class AgentService:
    async def get(self, agent_id: str):
        agent = await self.repo.get_by_id(agent_id)
        if not agent:
            raise HTTPException(404, "agent not found")   # ❌
        return agent
```

### Good — router is thin

```python
# app/api/v1/agents.py
@router.post("/", response_model=AgentResponse, status_code=201)
async def create_agent(
    payload: CreateAgentRequest,
    current_user: User = Depends(get_current_user),
    service: AgentService = Depends(get_agent_service),
) -> AgentResponse:
    agent = await service.create_agent(user_id=current_user.id, payload=payload)
    return AgentResponse.model_validate(agent)
```

### Good — service holds logic, raises domain errors

```python
# app/modules/agents/service.py
from app.core.errors import NotFoundError, PermissionDeniedError

class AgentService:
    def __init__(self, repository: AgentRepository):
        self.repository = repository

    async def create_agent(self, user_id: str, payload: CreateAgentRequest) -> Agent:
        return await self.repository.create(
            user_id=user_id,
            name=payload.name,
            role=payload.role,
            system_prompt=payload.system_prompt,
            model_provider=payload.model_provider,
            model_name=payload.model_name,
            tools_config=payload.tools,
            memory_config=payload.memory_config,
            guardrails_config=payload.guardrails,
        )

    async def get_agent(self, user_id: str, agent_id: str) -> Agent:
        agent = await self.repository.get_by_id(agent_id)
        if agent is None:
            raise NotFoundError("agent_not_found", f"agent {agent_id} not found")
        if agent.user_id != user_id:
            raise PermissionDeniedError("agent_forbidden", "not your agent")
        return agent
```

A global exception handler maps `NotFoundError` → 404, `PermissionDeniedError` → 403. See [[api-error-handling]].

### Good — repository is pure DB

```python
# app/modules/agents/repository.py
class AgentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **kwargs) -> Agent:
        agent = Agent(**kwargs)
        self.db.add(agent)
        await self.db.commit()
        await self.db.refresh(agent)
        return agent

    async def get_by_id(self, agent_id: str) -> Agent | None:
        result = await self.db.execute(select(Agent).where(Agent.id == agent_id))
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: str) -> list[Agent]:
        result = await self.db.execute(select(Agent).where(Agent.user_id == user_id))
        return list(result.scalars())
```

### Cross-module access

If `WorkflowService` needs to read an agent, it goes through `AgentService` — not `AgentRepository`. This keeps permission/business rules in one place.

```python
# ✅
class WorkflowService:
    def __init__(self, repo: WorkflowRepository, agent_service: AgentService):
        ...
    async def attach_agent(self, user_id: str, workflow_id: str, agent_id: str):
        await self.agent_service.get_agent(user_id, agent_id)   # permission-checked
        ...
```

See: [[module-domain-layout]], [[api-dependency-injection]], [[api-error-handling]]
