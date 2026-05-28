---
title: Consistent Response Shapes
impact: CRITICAL
impactDescription: Same envelope everywhere lets the React app share parsing + Zod schemas
tags: api, schemas, pagination
---

## Consistent Response Shapes

Three response shapes, used everywhere:

- **Single resource** — the resource model directly (`AgentResponse`)
- **Paginated list** — `PageResponse[T]`
- **Error** — standard error envelope from the global exception handler

### Paginated list

```python
# app/core/schemas.py
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class PageResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
```

Usage:

```python
@router.get("/", response_model=PageResponse[AgentResponse])
async def list_agents(
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    service: AgentService = Depends(get_agent_service),
) -> PageResponse[AgentResponse]:
    items, total = await service.list_agents(current_user.id, page, page_size)
    return PageResponse(
        items=[AgentResponse.model_validate(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
    )
```

### Single resource

```python
@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(...) -> AgentResponse:
    ...
```

Do not wrap single resources in `{ "data": ... }`. The shape *is* the resource.

### Error envelope

The global handler emits:

```json
{
  "error": {
    "code": "AGENT_NOT_FOUND",
    "message": "Agent not found",
    "details": {}
  }
}
```

See [[api-error-handling]] for the exception hierarchy that drives this.

### Response model conventions

- Always set `response_model=` on the route. This drives OpenAPI and prunes extra fields.
- Pydantic models that wrap ORM rows need `model_config = {"from_attributes": True}`.
- Pagination defaults: `page=1`, `page_size=20`. Cap `page_size` at 100 in the service layer.

### Bad — ad-hoc shapes

```python
# ❌ Three list endpoints, three different shapes
return agents                                # raw list
return {"data": agents, "count": len(agents)}  # custom wrapper
return {"results": agents, "next": None}       # DRF-style
```

### Good — one shape

```python
return PageResponse(items=agents, total=total, page=page, page_size=page_size)
```

See: [[api-error-handling]], [[arch-layering-separation]]
