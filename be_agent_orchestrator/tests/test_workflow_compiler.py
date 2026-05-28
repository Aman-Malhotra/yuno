"""Unit tests for the graph_json → compiled_graph normalization."""

from __future__ import annotations

from app.modules.workflows.compiler import (
    COMPILED_GRAPH_VERSION,
    compile_graph,
    validate_for_publish,
)
from app.modules.workflows.schemas import (
    WorkflowEdgeCondition,
    WorkflowGraph,
    WorkflowGraphEdge,
    WorkflowGraphNode,
)


def _agent_node(node_id: str, agent_id: str = "00000000-0000-0000-0000-000000000001"):
    return WorkflowGraphNode(
        id=node_id,
        type="agent",
        data={"label": node_id, "config": {"agentId": agent_id}},
    )


def test_compile_empty_graph_is_versioned_and_safe() -> None:
    compiled = compile_graph(WorkflowGraph(nodes=[], edges=[]))
    assert compiled["version"] == COMPILED_GRAPH_VERSION
    assert compiled["entry"] is None
    assert compiled["exits"] == []
    assert compiled["nodes"] == []
    assert compiled["edges"] == []
    assert compiled["conditional_edges"] == []


def test_compile_linear_graph_emits_simple_edges() -> None:
    graph = WorkflowGraph(
        nodes=[
            WorkflowGraphNode(id="start", type="start", data={"label": "start", "config": {}}),
            _agent_node("a"),
            WorkflowGraphNode(id="end", type="end", data={"label": "end", "config": {}}),
        ],
        edges=[
            WorkflowGraphEdge(id="e1", source="start", target="a"),
            WorkflowGraphEdge(id="e2", source="a", target="end"),
        ],
    )

    compiled = compile_graph(graph)

    assert compiled["entry"] == "start"
    assert compiled["exits"] == ["end"]
    assert compiled["conditional_edges"] == []
    sources = {(e["source"], e["target"]) for e in compiled["edges"]}
    assert sources == {("start", "a"), ("a", "end")}


def test_compile_groups_conditional_edges_by_source() -> None:
    graph = WorkflowGraph(
        nodes=[
            WorkflowGraphNode(id="start", type="start", data={"label": "start", "config": {}}),
            _agent_node("triage"),
            _agent_node("billing"),
            _agent_node("tech"),
            WorkflowGraphNode(id="end", type="end", data={"label": "end", "config": {}}),
        ],
        edges=[
            WorkflowGraphEdge(id="e_start", source="start", target="triage"),
            WorkflowGraphEdge(
                id="e_b",
                source="triage",
                target="billing",
                condition=WorkflowEdgeCondition(kind="equals", path="intent", value="billing"),
            ),
            WorkflowGraphEdge(
                id="e_t",
                source="triage",
                target="tech",
                condition=WorkflowEdgeCondition(kind="equals", path="intent", value="tech"),
            ),
            WorkflowGraphEdge(id="e_default", source="triage", target="end"),
            WorkflowGraphEdge(id="e_b_end", source="billing", target="end"),
            WorkflowGraphEdge(id="e_t_end", source="tech", target="end"),
        ],
    )

    compiled = compile_graph(graph)

    # The triage source carries 2 conditional branches + 1 default → grouped
    # into a single `add_conditional_edges` entry.
    cond = [c for c in compiled["conditional_edges"] if c["source"] == "triage"]
    assert len(cond) == 1
    branches = cond[0]["branches"]
    targets = [b["target"] for b in branches]
    assert "billing" in targets
    assert "tech" in targets
    # The default branch is appended last and marked as such.
    assert branches[-1]["target"] == "end"
    assert branches[-1]["is_default"] is True

    # The triage→end "always" edge must not also show up in simple edges,
    # because it became the default branch above.
    simple_sources = {(e["source"], e["target"]) for e in compiled["edges"]}
    assert ("triage", "end") not in simple_sources
    # Other plain edges still go through the simple bucket.
    assert ("start", "triage") in simple_sources
    assert ("billing", "end") in simple_sources
    assert ("tech", "end") in simple_sources


def test_compile_skips_dangling_edges() -> None:
    # Editor briefly holds half-connected edges mid-drag; the compiler
    # tolerates them so autosave never rejects an in-progress canvas.
    graph = WorkflowGraph(
        nodes=[_agent_node("a")],
        edges=[
            WorkflowGraphEdge(id="ghost", source="a", target="nonexistent"),
        ],
    )
    compiled = compile_graph(graph)
    assert compiled["edges"] == []
    assert compiled["conditional_edges"] == []


def test_validate_for_publish_flags_missing_start_and_end() -> None:
    issues = validate_for_publish(WorkflowGraph(nodes=[_agent_node("a")], edges=[]))
    codes = {i.code for i in issues}
    assert "missing_start" in codes
    assert "missing_end" in codes


def test_validate_for_publish_flags_edge_into_start() -> None:
    graph = WorkflowGraph(
        nodes=[
            WorkflowGraphNode(id="start", type="start", data={"label": "start", "config": {}}),
            _agent_node("a"),
            WorkflowGraphNode(id="end", type="end", data={"label": "end", "config": {}}),
        ],
        edges=[
            WorkflowGraphEdge(id="bad", source="a", target="start"),
            WorkflowGraphEdge(id="ok", source="start", target="a"),
            WorkflowGraphEdge(id="ok2", source="a", target="end"),
        ],
    )
    codes = {i.code for i in validate_for_publish(graph)}
    assert "edge_into_start" in codes


def test_validate_for_publish_accepts_valid_minimal_graph() -> None:
    graph = WorkflowGraph(
        nodes=[
            WorkflowGraphNode(id="start", type="start", data={"label": "start", "config": {}}),
            _agent_node("a"),
            WorkflowGraphNode(id="end", type="end", data={"label": "end", "config": {}}),
        ],
        edges=[
            WorkflowGraphEdge(id="e1", source="start", target="a"),
            WorkflowGraphEdge(id="e2", source="a", target="end"),
        ],
    )
    assert validate_for_publish(graph) == []
