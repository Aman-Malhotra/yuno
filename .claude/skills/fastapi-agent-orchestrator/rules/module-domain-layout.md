---
title: Domain Module Layout
impact: CRITICAL
impactDescription: Every module looks the same, so navigating the codebase is mechanical
tags: architecture, modules, conventions
---

## Domain Module Layout

Every folder under `app/modules/` follows the same five-file pattern:

```txt
modules/<domain>/
  models.py        # SQLAlchemy ORM models (DB schema)
  schemas.py       # Pydantic v2 request/response/event schemas
  repository.py    # DB queries — no business logic
  service.py       # business logic, permissions, orchestration
  router.py        # FastAPI APIRouter — HTTP only
```

Some modules add extras (kept inside the same folder):

| Module       | Extra files                                                                  |
|--------------|------------------------------------------------------------------------------|
| `auth/`      | `dependencies.py` (`get_current_user`, etc.)                                 |
| `workflows/` | `graph_schema.py`, `graph_validator.py`                                      |
| `tools/`     | `registry.py`, `builtins/calculator.py`, `builtins/web_search.py`, ...       |
| `llm/`       | `registry.py`, `providers/base.py`, `providers/openai_provider.py`, ...      |
| `channels/`  | `registry.py`, `providers/telegram.py`, `webhooks/telegram.py`               |
| `runtime/`   | `workflow_compiler.py`, `langgraph_runtime.py`, `agent_executor.py`, `events.py`, `state.py` |
| `monitoring/`| `connection_manager.py`, `event_publisher.py`                                |

### Example: `modules/agents/`

```python
# models.py
from datetime import datetime
from sqlalchemy import String, JSON, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    system_prompt: Mapped[str] = mapped_column(String)
    model_provider: Mapped[str] = mapped_column(String)
    model_name: Mapped[str] = mapped_column(String)
    temperature: Mapped[float] = mapped_column(default=0.7)
    tools_config: Mapped[dict] = mapped_column(JSON, default=dict)
    memory_config: Mapped[dict] = mapped_column(JSON, default=dict)
    schedule_config: Mapped[dict] = mapped_column(JSON, default=dict)
    guardrails_config: Mapped[dict] = mapped_column(JSON, default=dict)
    channel_config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
```

```python
# schemas.py
from pydantic import BaseModel, Field


class ToolConfig(BaseModel):
    name: str
    options: dict = Field(default_factory=dict)


class CreateAgentRequest(BaseModel):
    name: str
    role: str
    description: str | None = None
    system_prompt: str
    model_provider: str
    model_name: str
    temperature: float = 0.7
    tools: list[ToolConfig] = Field(default_factory=list)
    memory_config: dict = Field(default_factory=dict)
    schedule_config: dict = Field(default_factory=dict)
    guardrails: dict = Field(default_factory=dict)


class AgentResponse(BaseModel):
    id: str
    name: str
    role: str
    model_provider: str
    model_name: str

    model_config = {"from_attributes": True}
```

```python
# repository.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Agent


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

```python
# service.py
from app.core.errors import NotFoundError, PermissionDeniedError

from .repository import AgentRepository
from .schemas import CreateAgentRequest
from .models import Agent


class AgentService:
    def __init__(self, repository: AgentRepository):
        self.repository = repository

    async def create_agent(self, user_id: str, payload: CreateAgentRequest) -> Agent:
        return await self.repository.create(
            user_id=user_id,
            name=payload.name,
            role=payload.role,
            description=payload.description,
            system_prompt=payload.system_prompt,
            model_provider=payload.model_provider,
            model_name=payload.model_name,
            temperature=payload.temperature,
            tools_config=[t.model_dump() for t in payload.tools],
            memory_config=payload.memory_config,
            schedule_config=payload.schedule_config,
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

```python
# router.py
from fastapi import APIRouter, Depends

from app.api.deps import get_agent_service, get_current_user
from app.modules.users.models import User

from .schemas import CreateAgentRequest, AgentResponse
from .service import AgentService


router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/", response_model=AgentResponse, status_code=201)
async def create_agent(
    payload: CreateAgentRequest,
    current_user: User = Depends(get_current_user),
    service: AgentService = Depends(get_agent_service),
) -> AgentResponse:
    agent = await service.create_agent(user_id=current_user.id, payload=payload)
    return AgentResponse.model_validate(agent)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    service: AgentService = Depends(get_agent_service),
) -> AgentResponse:
    agent = await service.get_agent(current_user.id, agent_id)
    return AgentResponse.model_validate(agent)
```

### Rules

- One ORM model class per concept, in that module's `models.py`
- Request and response schemas live in `schemas.py`, not on the model
- Repositories never raise `HTTPException`
- Services never construct `Response` / `JSONResponse`
- Routers never run SQL

See: [[arch-layering-separation]], [[arch-project-structure]], [[api-dependency-injection]]
