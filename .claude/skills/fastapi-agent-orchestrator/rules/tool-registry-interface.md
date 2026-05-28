---
title: Tool Registry + `Tool` ABC
impact: HIGH
impactDescription: Tools are referenced by name in agent config (JSONB) — a registry maps name → impl with a uniform interface
tags: tools, registry, plugin
---

## Tool Registry + `Tool` ABC

Each tool implements one interface. The registry maps `name → Tool` at startup. Agents reference tools by name in their `tools_config`.

### Base interface

```python
# app/modules/tools/registry.py
from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Any


class ToolDescriptor(BaseModel):
    name: str
    description: str
    parameters_schema: dict   # JSON Schema for the LLM


class Tool(ABC):
    name: str
    description: str
    parameters_schema: dict

    @abstractmethod
    async def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        ...

    def descriptor(self) -> ToolDescriptor:
        return ToolDescriptor(
            name=self.name,
            description=self.description,
            parameters_schema=self.parameters_schema,
        )
```

### Built-ins

```txt
app/modules/tools/builtins/
  calculator.py
  web_search.py
  mock_crm.py
  email_summary.py
  task_planner.py
```

```python
# app/modules/tools/builtins/calculator.py
from ..registry import Tool


class CalculatorTool(Tool):
    name = "calculator"
    description = "Evaluate a math expression. Input: {expression: str}"
    parameters_schema = {
        "type": "object",
        "properties": {"expression": {"type": "string"}},
        "required": ["expression"],
    }

    async def execute(self, input_data):
        expr = input_data["expression"]
        # use a safe evaluator, not eval(); for the assignment, numexpr is fine
        import numexpr as ne
        return {"result": float(ne.evaluate(expr))}
```

### Registry construction

```python
# app/modules/tools/registry.py (continued)
from .builtins.calculator import CalculatorTool
from .builtins.web_search import WebSearchTool
from .builtins.mock_crm import MockCrmTool
from .builtins.email_summary import EmailSummaryTool


def build_tool_registry() -> dict[str, Tool]:
    return {t.name: t for t in [
        CalculatorTool(),
        WebSearchTool(),
        MockCrmTool(),
        EmailSummaryTool(),
    ]}
```

### Service

```python
# app/modules/tools/service.py
from .registry import Tool, ToolDescriptor


class ToolService:
    def __init__(self, registry: dict[str, Tool]):
        self.registry = registry

    def list(self) -> list[ToolDescriptor]:
        return [t.descriptor() for t in self.registry.values()]

    def descriptors_for(self, tools_config: list[dict]) -> list[ToolDescriptor]:
        return [self.registry[c["name"]].descriptor() for c in tools_config if c["name"] in self.registry]

    async def execute(self, name: str, input_data: dict) -> dict:
        tool = self.registry.get(name)
        if tool is None:
            raise NotFoundError("tool_not_found", f"tool {name} not registered")
        return await tool.execute(input_data)
```

### Endpoints

```python
# app/modules/tools/router.py
router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("/", response_model=list[ToolDescriptor])
async def list_tools(service: ToolService = Depends(get_tool_service)):
    return service.list()


@router.post("/{tool_name}/test")
async def test_tool(
    tool_name: str,
    payload: dict,
    service: ToolService = Depends(get_tool_service),
):
    return await service.execute(tool_name, payload)
```

### Bad — tools as free functions on a god-class

```python
# ❌ Hard to discover, hard to add new ones safely
class ToolService:
    async def calculator(self, expr: str): ...
    async def web_search(self, q: str): ...
    async def mock_crm(self, customer_id: str): ...
```

### Bad — calling `eval()` for the calculator

```python
# ❌ Code execution in your agent runtime
result = eval(expr)
```

### Adding a new tool (instructions for the README)

1. Create `app/modules/tools/builtins/<name>.py` with a class extending `Tool`
2. Set `name`, `description`, `parameters_schema`
3. Add to `build_tool_registry()`
4. Done — the React UI's tool picker reads `GET /api/v1/tools`

### Rules

- Every tool is a class extending `Tool` with `name`, `description`, `parameters_schema`, `execute`
- The registry is built once at startup
- Agent `tools_config` is `[{"name": "calculator", "options": {...}}]` — names match registry keys
- The executor passes `descriptors_for(agent.tools_config)` to the LLM; LLM picks tools by name; executor dispatches via `service.execute(name, input)`
- `parameters_schema` is valid JSON Schema — the LLM provider passes it through to the model

See: [[runtime-agent-executor]], [[llm-provider-abstraction]], [[module-domain-layout]]
