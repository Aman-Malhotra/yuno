"""Normalize the React Flow graph into a langgraph-ready intermediate form.

The persisted `graph_json` is the editor's source of truth — positions,
opaque per-node payloads, autosave-friendly. The `compiled_graph` we
derive here is what the runtime dispatcher feeds into a `StateGraph` to
materialize the actual langgraph at run time. Keeping the two separate
means:

* the editor can ship layout-only updates without us having to re-derive
  runtime intent every keystroke, and
* the runtime never has to interpret React Flow's UI fields — it just
  reads a flat, normalized shape.

Conditional edges follow langgraph's `add_conditional_edges` pattern:
multiple outgoing edges from the same source whose ``condition.kind`` is
not ``always`` are grouped into a single ``conditional_edges`` entry with
ordered branches; an `always` edge becomes the default branch.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.modules.workflows.schemas import (
    WorkflowGraph,
    WorkflowGraphEdge,
    WorkflowGraphNode,
)

COMPILED_GRAPH_VERSION = 1


def compile_graph(graph: WorkflowGraph) -> dict[str, Any]:
    """Normalize ``graph_json`` into the runtime-ready ``compiled_graph``.

    Lenient by design — the editor calls this on every autosave, including
    half-built graphs (no start, dangling edges, agent nodes without an
    ``agentId``). Strict invariants (start required, no orphan nodes, etc.)
    are enforced separately at publish time by ``validate_for_publish``.
    """

    nodes_by_id = {n.id: n for n in graph.nodes}
    start_id = next((n.id for n in graph.nodes if n.type == "start"), None)
    end_ids = [n.id for n in graph.nodes if n.type == "end"]

    compiled_nodes = [_compile_node(n) for n in graph.nodes]

    # Group outgoing edges by source so we can decide simple vs. conditional.
    outgoing: dict[str, list[WorkflowGraphEdge]] = defaultdict(list)
    for edge in graph.edges:
        # Skip dangling edges silently — the editor may briefly hold them
        # mid-connection. Strict checks live in ``validate_for_publish``.
        if edge.source not in nodes_by_id or edge.target not in nodes_by_id:
            continue
        outgoing[edge.source].append(edge)

    simple_edges: list[dict[str, Any]] = []
    conditional_edges: list[dict[str, Any]] = []

    for source_id, edges in outgoing.items():
        conditional = [e for e in edges if e.condition and e.condition.kind != "always"]
        if not conditional:
            for edge in edges:
                simple_edges.append(_compile_simple_edge(edge))
            continue

        # Mixed bag: some conditional, some unconditional → langgraph
        # `add_conditional_edges` with the unconditional ones as the default
        # branch (matches the user mental model: "if nothing matches, go here").
        branches: list[dict[str, Any]] = []
        for edge in conditional:
            branches.append(
                {
                    "target": edge.target,
                    "condition": edge.condition.model_dump(exclude_none=True),  # type: ignore[union-attr]
                    "label": edge.label,
                }
            )
        defaults = [e for e in edges if not e.condition or e.condition.kind == "always"]
        if defaults:
            branches.append(
                {
                    "target": defaults[0].target,
                    "condition": {"kind": "always"},
                    "label": defaults[0].label,
                    "is_default": True,
                }
            )
        conditional_edges.append(
            {
                "source": source_id,
                "branches": branches,
            }
        )

    return {
        "version": COMPILED_GRAPH_VERSION,
        "entry": start_id,
        "exits": end_ids,
        "nodes": compiled_nodes,
        "edges": simple_edges,
        "conditional_edges": conditional_edges,
    }


def _compile_node(node: WorkflowGraphNode) -> dict[str, Any]:
    config = node.data.get("config", {}) if isinstance(node.data, dict) else {}
    compiled: dict[str, Any] = {
        "id": node.id,
        "type": node.type,
        "label": node.data.get("label") if isinstance(node.data, dict) else None,
    }
    if node.type == "agent":
        compiled["agent_id"] = config.get("agentId")
        compiled["input_template"] = config.get("input")
    elif node.type == "tool":
        compiled["tool_id"] = config.get("toolId")
        compiled["input"] = config.get("input")
    elif node.type == "condition":
        compiled["expression"] = config.get("expression")
    return compiled


def _compile_simple_edge(edge: WorkflowGraphEdge) -> dict[str, Any]:
    return {
        "source": edge.source,
        "target": edge.target,
        "label": edge.label,
    }


# ──────────────────────────────────────────────────────────────────────
# Strict validation — used at publish time, not autosave
# ──────────────────────────────────────────────────────────────────────


class GraphValidationIssue:
    __slots__ = ("code", "message", "details")

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": self.details}


def validate_for_publish(graph: WorkflowGraph) -> list[GraphValidationIssue]:
    """Strict structural validation. Returns an empty list when graph is shippable."""

    issues: list[GraphValidationIssue] = []
    node_ids = {n.id for n in graph.nodes}

    starts = [n for n in graph.nodes if n.type == "start"]
    if not starts:
        issues.append(GraphValidationIssue("missing_start", "Workflow must have a start node."))
    elif len(starts) > 1:
        issues.append(
            GraphValidationIssue(
                "multiple_start",
                "Workflow has multiple start nodes.",
                {"node_ids": [n.id for n in starts]},
            )
        )

    if not any(n.type == "end" for n in graph.nodes):
        issues.append(
            GraphValidationIssue("missing_end", "Workflow must have at least one end node.")
        )

    start_ids = {n.id for n in starts}
    for edge in graph.edges:
        if edge.source not in node_ids:
            issues.append(
                GraphValidationIssue(
                    "edge_unknown_source",
                    f"Edge {edge.id} references unknown source node.",
                    {"edge_id": edge.id, "source": edge.source},
                )
            )
        if edge.target not in node_ids:
            issues.append(
                GraphValidationIssue(
                    "edge_unknown_target",
                    f"Edge {edge.id} references unknown target node.",
                    {"edge_id": edge.id, "target": edge.target},
                )
            )
        if edge.target in start_ids:
            issues.append(
                GraphValidationIssue(
                    "edge_into_start",
                    f"Edge {edge.id} targets a start node.",
                    {"edge_id": edge.id, "target": edge.target},
                )
            )

    for node in graph.nodes:
        config = node.data.get("config", {}) if isinstance(node.data, dict) else {}
        if node.type == "agent" and not config.get("agentId"):
            issues.append(
                GraphValidationIssue(
                    "agent_node_missing_agent",
                    f"Agent node {node.id} has no agentId.",
                    {"node_id": node.id},
                )
            )
        if node.type == "tool" and not config.get("toolId"):
            issues.append(
                GraphValidationIssue(
                    "tool_node_missing_tool",
                    f"Tool node {node.id} has no toolId.",
                    {"node_id": node.id},
                )
            )

    return issues
