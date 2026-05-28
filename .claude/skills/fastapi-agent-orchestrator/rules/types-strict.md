---
title: Strict Type Annotations Everywhere
impact: CRITICAL
impactDescription: Untyped Python rots fast — silently passing the wrong shape into a service or a JSONB blob is the #1 source of late-night bugs
tags: types, mypy, typing, discipline
---

## Strict Type Annotations Everywhere

Every variable, every function arg, every return type, every class attribute is **explicitly typed**. No implicit `Any`, no untyped `dict`, no bare `list`.

The project runs `mypy --strict`. CI fails on missing types.

### Rules

- All function signatures: parameters + return type — including `-> None`
- All class attributes: typed at the class level (`Mapped[T]` for ORM, `:` annotation for plain classes)
- All Pydantic models: every field typed (Pydantic enforces this, but spell out unions and `| None`)
- Collections: parameterized — `list[Agent]`, `dict[str, ToolDescriptor]`, not bare `list`/`dict`
- Loop variables: when not obvious from the iterable, annotate (`for event: RuntimeEvent in events:`)
- `Any` is **banned** outside of two places: the JSONB freeform `dict[str, Any]` boundary and a clearly-marked `# type: ignore[no-any-return]` with a one-line reason
- TypedDict or Pydantic model for any dict with a known shape — never `dict[str, str | int | bool]`

### `pyproject.toml`

```toml
[tool.mypy]
python_version = "3.11"
strict = true
plugins = ["pydantic.mypy"]
warn_unused_ignores = true
warn_return_any = true
disallow_any_generics = true
disallow_untyped_calls = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true
```

### Bad — implicit `Any`

```python
# ❌ inputs untyped, return untyped, body uses Any
def create_agent(payload, user):
    agent = build(payload)
    return agent
```

### Bad — bare collections

```python
# ❌ what's in the list?
def list_agents() -> list:
    ...

# ❌ what's in the dict?
def make_registry() -> dict:
    ...
```

### Bad — untyped loop / comprehension when it matters

```python
# ❌ `event` is inferred from a heterogeneous source — easy to misuse
for event in raw_events:
    publish(event)
```

```python
# ❌ Pydantic model field is `dict` — could be anything
class CreateAgentRequest(BaseModel):
    config: dict
```

### Bad — `**kwargs: Any` to "stay flexible"

```python
# ❌ Type system gives up; refactors break silently
async def create(self, **kwargs: Any) -> Agent:
    ...
```

Replace with an explicit Pydantic model or TypedDict for the payload.

### Good — explicit types everywhere

```python
# ✅ signature + locals + return
async def create_agent(
    self,
    user_id: str,
    payload: CreateAgentRequest,
) -> Agent:
    tools_payload: list[dict[str, Any]] = [t.model_dump() for t in payload.tools]
    agent: Agent = await self.repository.create(
        user_id=user_id,
        name=payload.name,
        role=payload.role,
        system_prompt=payload.system_prompt,
        model_provider=payload.model_provider,
        model_name=payload.model_name,
        tools_config=tools_payload,
    )
    return agent
```

```python
# ✅ parameterized collection + branded id-style aliases when useful
AgentId = str  # promote to NewType("AgentId", str) once the surface is large
AgentsByUser = dict[str, list[Agent]]


def group_by_user(agents: list[Agent]) -> AgentsByUser:
    out: AgentsByUser = {}
    for agent in agents:
        out.setdefault(agent.user_id, []).append(agent)
    return out
```

### Good — typed loop / event handler

```python
# ✅ event variable typed explicitly because the source is `Any`-ish
async def fan_out(messages: AsyncIterator[bytes]) -> None:
    async for message in messages:
        event: RuntimeEvent = RuntimeEvent.model_validate_json(message)
        await broadcast(event)
```

### Good — TypedDict for known-shape dicts

```python
from typing import TypedDict


class ToolCallDict(TypedDict):
    id: str
    name: str
    arguments: dict[str, Any]


def parse_call(raw: dict[str, Any]) -> ToolCallDict:
    return {"id": raw["id"], "name": raw["name"], "arguments": raw["arguments"]}
```

### The one allowed escape hatch

JSONB payloads (`payload: dict[str, Any]` on `RuntimeEvent`, run input/output, message metadata) are intentionally freeform — they cross a serialization boundary. **At every call site that produces or consumes them**, validate into a Pydantic model on the way out:

```python
# producing
await emit.emit(
    RuntimeEventType.LLM_RESPONSE,
    payload=LlmResponsePayload(
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
    ).model_dump(),
)

# consuming
payload = LlmResponsePayload.model_validate(event.payload)
total += payload.input_tokens
```

### Pre-commit + CI

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/astral-sh/ruff-pre-commit
  rev: v0.6.0
  hooks:
    - id: ruff
    - id: ruff-format
- repo: https://github.com/pre-commit/mirrors-mypy
  rev: v1.10.0
  hooks:
    - id: mypy
      args: [--strict]
      additional_dependencies:
        - pydantic
        - sqlalchemy
```

CI runs `uv run mypy app` on every PR. A type error blocks the merge.

### Rules (short)

- Functions: typed args + return, always
- Classes: typed attributes, always
- Collections: parameterized, always
- `Any` only across JSONB boundaries — and immediately validated into a Pydantic model
- `# type: ignore` requires a one-line comment explaining why
- `mypy --strict` is part of the test gate, not optional

See: [[module-domain-layout]], [[db-schema-jsonb]], [[realtime-event-schema]]
