---
title: Workflow JSON → LangGraph Compiler
impact: CRITICAL
impactDescription: The visual workflow IS the executable; the compiler is the contract between the React Flow canvas and LangGraph
tags: runtime, langgraph, compiler
---

## Workflow JSON → LangGraph Compiler

The compiler is a **pure function**: given a validated `WorkflowGraph` + an agent loader, it returns a compiled LangGraph `StateGraph`. No side effects, no I/O — it just builds the graph. This makes it trivially unit-testable.

### Contract

```python
# app/modules/runtime/workflow_compiler.py
from typing import Callable, Awaitable
from langgraph.graph import StateGraph, END

from app.modules.workflows.schemas import WorkflowGraph
from app.modules.agents.models import Agent

from .state import RuntimeState
from .agent_executor import build_agent_node


AgentLoader = Callable[[str], Awaitable[Agent]]


def compile_workflow(
    graph: WorkflowGraph,
    load_agent: AgentLoader,
    emit: "EventEmitter",
) -> StateGraph:
    sg = StateGraph(RuntimeState)

    # 1) nodes
    for node in graph.nodes:
        if node.type == "agent":
            agent_id = node.data["agent_id"]
            sg.add_node(node.id, build_agent_node(node.id, agent_id, load_agent, emit))
        elif node.type == "tool":
            sg.add_node(node.id, build_tool_node(node.id, node.data, emit))
        elif node.type == "condition":
            # condition node is virtual; handled in edge routing below
            sg.add_node(node.id, _passthrough_node(node.id, emit))
        else:
            raise ValueError(f"unknown node type: {node.type}")

    # 2) entry point
    entry = next(n for n in graph.nodes if n.data.get("is_entry"))
    sg.set_entry_point(entry.id)

    # 3) edges
    edges_by_source: dict[str, list] = {}
    for edge in graph.edges:
        edges_by_source.setdefault(edge.source, []).append(edge)

    for source, outgoing in edges_by_source.items():
        if len(outgoing) == 1 and outgoing[0].condition is None:
            target = outgoing[0].target
            sg.add_edge(source, END if target == "__end__" else target)
        else:
            sg.add_conditional_edges(source, _router(outgoing))

    return sg.compile()


def _router(edges):
    def route(state: RuntimeState) -> str:
        for edge in edges:
            if edge.condition is None or _eval_condition(edge.condition, state):
                return END if edge.target == "__end__" else edge.target
        return END
    return route
```

### Why pure

- Easy to test with a stubbed `load_agent` + an in-memory event sink
- Same compiler runs for "test workflow" (one-off, no persistence) and "real run" (worker, persists everything)
- Frontend can call `POST /workflows/{id}/validate` which runs the compiler + a dry executor

### Validation lives next to the compiler

```python
# app/modules/workflows/graph_validator.py
from app.core.errors import ValidationError
from .schemas import WorkflowGraph


def validate_graph(graph: WorkflowGraph) -> None:
    node_ids = {n.id for n in graph.nodes}

    entries = [n for n in graph.nodes if n.data.get("is_entry")]
    if len(entries) != 1:
        raise ValidationError("invalid_graph", "exactly one entry node required")

    for edge in graph.edges:
        if edge.source not in node_ids:
            raise ValidationError("invalid_edge", f"edge.source {edge.source} not a node")
        if edge.target not in node_ids and edge.target != "__end__":
            raise ValidationError("invalid_edge", f"edge.target {edge.target} not a node")

    if _has_unreachable_nodes(graph):
        raise ValidationError("unreachable_nodes", "some nodes are not reachable from entry")
```

Call from the service:

```python
class WorkflowService:
    async def validate(self, user_id: str, workflow_id: str) -> None:
        wf = await self.get(user_id, workflow_id)
        graph = WorkflowGraph.model_validate(wf.graph_json)
        validate_graph(graph)
```

### Bad — putting DB queries inside the compiler

```python
# ❌ Compiler is no longer pure; can't unit-test without a database
def compile_workflow(workflow_id: str, db: AsyncSession) -> StateGraph:
    wf = db.execute(...).scalar_one()
    ...
```

### Bad — mixing executor logic into the compiler

The compiler **builds** the graph. The executor **runs** it. They live in different files (`workflow_compiler.py` vs `langgraph_runtime.py`).

### Rules

- `compile_workflow(graph, load_agent, emit) -> CompiledGraph` — no DB, no Redis, no HTTP
- Validation is a separate pure function in the workflows module
- Node-type registry is open: adding a new node type means a new `build_*_node()` factory + a new branch in the compiler
- Conditional edges use `add_conditional_edges`; loops are just edges that point back to an earlier node

See: [[runtime-event-emission]], [[runtime-agent-executor]], [[db-schema-jsonb]]
