---
title: Use JSONB for Graph + Config Blobs
impact: CRITICAL
impactDescription: The visual workflow + agent configs are deeply variable — modeling them as relational tables would explode complexity
tags: db, jsonb, postgres
---

## Use JSONB for Graph + Config Blobs

Pydantic is the schema for these fields. The DB stores them as JSONB. Validation happens at the service boundary, not via SQL constraints.

### What goes in JSONB

| Table              | JSONB column          | Pydantic schema                                  |
|--------------------|-----------------------|--------------------------------------------------|
| `agents`           | `tools_config`        | `list[ToolConfig]`                               |
| `agents`           | `memory_config`       | `MemoryConfig`                                   |
| `agents`           | `schedule_config`     | `ScheduleConfig`                                 |
| `agents`           | `guardrails_config`   | `GuardrailsConfig`                               |
| `agents`           | `channel_config`      | `ChannelConfig`                                  |
| `workflows`        | `graph_json`          | `WorkflowGraph` (nodes + edges + conditions)     |
| `workflow_runs`    | `input`, `output`     | freeform `dict`                                  |
| `runtime_events`   | `payload`             | per-event-type `dict`                            |
| `agent_messages`   | `metadata`            | freeform `dict`                                  |

### Column declaration

```python
# app/modules/workflows/models.py
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin


class Workflow(Base, IdMixin, TimestampMixin):
    __tablename__ = "workflows"

    user_id: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    graph_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String, default="draft")
```

Use `from sqlalchemy.dialects.postgresql import JSONB` — not the generic `JSON` — so we get `jsonb` not `json`. JSONB supports indexes and `->>` queries.

### Validate at the service boundary

```python
# app/modules/workflows/schemas.py
from pydantic import BaseModel, Field


class WorkflowNode(BaseModel):
    id: str
    type: str
    data: dict


class WorkflowEdge(BaseModel):
    id: str
    source: str
    target: str
    condition: str | None = None


class WorkflowGraph(BaseModel):
    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge]


class CreateWorkflowRequest(BaseModel):
    name: str
    description: str | None = None
    graph: WorkflowGraph
```

```python
# app/modules/workflows/service.py
class WorkflowService:
    async def create(self, user_id: str, payload: CreateWorkflowRequest) -> Workflow:
        validate_graph(payload.graph)   # pure function, raises ValidationError
        return await self.repo.create(
            user_id=user_id,
            name=payload.name,
            description=payload.description,
            graph_json=payload.graph.model_dump(),
            status="draft",
        )
```

### Read path: parse back into Pydantic

```python
class WorkflowResponse(BaseModel):
    id: str
    name: str
    description: str | None
    graph: WorkflowGraph
    status: str

    @classmethod
    def from_orm_row(cls, row: Workflow) -> "WorkflowResponse":
        return cls(
            id=row.id,
            name=row.name,
            description=row.description,
            graph=WorkflowGraph.model_validate(row.graph_json),
            status=row.status,
        )
```

### Indexing JSONB

For fields you filter by frequently:

```sql
CREATE INDEX agents_tools_gin ON agents USING GIN (tools_config jsonb_path_ops);
```

Add in an Alembic migration only when a query is actually slow. Don't pre-emptively GIN-index every JSONB column.

### Bad — modeling JSONB as relational

```python
# ❌ A `workflow_nodes` + `workflow_edges` + `workflow_node_data` table set
# for a feature that's edited as one JSON blob in the React Flow canvas.
```

You spend the assignment time on join boilerplate and lose the ability to ship freeform node data.

### Bad — storing JSON as `String`

```python
# ❌ No JSONB operators, manual json.loads everywhere
graph_json: Mapped[str] = mapped_column(String)
```

### Rules

- JSONB for: workflow graphs, agent configs (tools/memory/guardrails/schedules), event payloads, message metadata
- Relational columns for: foreign keys, status enums, timestamps, anything you filter / order / index by
- Pydantic owns the JSONB shape; the migration only knows it's `JSONB`
- Add a GIN index only when you've proved a slow query, not before

See: [[module-domain-layout]], [[db-alembic-migrations]], [[runtime-workflow-compiler]]
