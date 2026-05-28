from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

WorkflowStatus = Literal["draft", "published", "archived"]

# ──────────────────────────────────────────────────────────────────────
# Graph shape (React Flow ⇄ langgraph round-trip)
# ──────────────────────────────────────────────────────────────────────
#
# The persisted `graph_json` is the raw React Flow surface (positions, UI
# state, opaque per-node config). The `compiled_graph` is the normalized,
# runtime-ready shape the langgraph dispatcher will read at run time —
# kept separate so the editor can ship layout-only updates without us
# having to re-derive runtime intent server-side every keystroke.

WorkflowNodeType = Literal["start", "agent", "tool", "condition", "end"]
EdgeConditionKind = Literal["always", "equals", "expr"]


class WorkflowEdgeCondition(BaseModel):
    """Routing predicate on a graph edge.

    `always`  — unconditional (default when omitted)
    `equals`  — `state[path] == value`
    `expr`    — safe DSL expression (parsed at compile time, not eval'd here)
    """

    kind: EdgeConditionKind = "always"
    path: str | None = Field(default=None, max_length=240)
    value: Any = None
    expr: str | None = Field(default=None, max_length=2000)

    model_config = ConfigDict(extra="forbid")


class WorkflowGraphNode(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    type: WorkflowNodeType
    position: dict[str, float] = Field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    data: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Opaque per-node payload. The builder writes `label` + `config`; "
            "the compiler reads `config.agentId` / `config.toolId` / `config.expression` "
            "depending on the node type."
        ),
    )

    model_config = ConfigDict(extra="allow")


class WorkflowGraphEdge(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    source: str = Field(min_length=1, max_length=120)
    target: str = Field(min_length=1, max_length=120)
    label: str | None = Field(default=None, max_length=240)
    condition: WorkflowEdgeCondition | None = None

    model_config = ConfigDict(extra="allow")


class WorkflowGraph(BaseModel):
    """Raw React Flow graph as stored in `workflows.graph_json`."""

    nodes: list[WorkflowGraphNode] = Field(default_factory=list)
    edges: list[WorkflowGraphEdge] = Field(default_factory=list)
    viewport: dict[str, Any] | None = Field(
        default=None,
        description="Optional React Flow viewport (`{x, y, zoom}`).",
    )

    model_config = ConfigDict(extra="forbid")


# ──────────────────────────────────────────────────────────────────────
# Requests
# ──────────────────────────────────────────────────────────────────────


class CreateWorkflowRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    graph: WorkflowGraph | None = Field(
        default=None,
        description="Optional initial graph; defaults to an empty canvas with a single `start` node.",
    )
    settings: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be blank")
        return v

    model_config = ConfigDict(extra="forbid")


class UpdateWorkflowRequest(BaseModel):
    """Partial update for non-graph workflow metadata."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    status: WorkflowStatus | None = None
    settings: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid")


class UpdateWorkflowGraphRequest(BaseModel):
    """Dedicated PATCH body for autosave from the canvas.

    The editor debounces every node/edge change and ships this payload —
    keeping it separate from `UpdateWorkflowRequest` means the autosave
    path is cheap to validate and never accidentally mutates name/status.
    """

    graph: WorkflowGraph

    model_config = ConfigDict(extra="forbid")


# ──────────────────────────────────────────────────────────────────────
# Responses
# ──────────────────────────────────────────────────────────────────────


class WorkflowSummary(BaseModel):
    """Light shape for list endpoints — no graph_json (kilobytes+ per row)."""

    id: UUID
    workspace_id: UUID
    name: str
    slug: str
    description: str | None = None
    status: WorkflowStatus
    created_by: UUID | None = Field(
        default=None,
        description="User who authored the workflow. Null if that user was deleted.",
    )
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "01HZX9F4Y0N0N5J5R0Q6Z3M8B2",
                    "workspace_id": "01HZX9F4Y0N0N5J5R0Q6Z3M8AA",
                    "name": "Support triage",
                    "slug": "support-triage",
                    "description": "Routes inbound questions to the right specialist agent.",
                    "status": "draft",
                    "created_by": "01HZX9F4Y0N0N5J5R0Q6Z3M8AB",
                    "created_at": "2026-05-23T18:42:13.812000Z",
                    "updated_at": "2026-05-23T18:50:00.000000Z",
                }
            ]
        },
    )


class WorkflowDetail(BaseModel):
    """Full workflow — includes graph_json + compiled_graph + settings."""

    id: UUID
    workspace_id: UUID
    name: str
    slug: str
    description: str | None = None
    status: WorkflowStatus

    graph: WorkflowGraph
    compiled_graph: dict[str, Any] = Field(default_factory=dict)
    settings: dict[str, Any] = Field(default_factory=dict)

    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_workflow(cls, workflow: object) -> "WorkflowDetail":
        return cls(
            id=workflow.id,  # type: ignore[attr-defined]
            workspace_id=workflow.workspace_id,  # type: ignore[attr-defined]
            name=workflow.name,  # type: ignore[attr-defined]
            slug=workflow.slug,  # type: ignore[attr-defined]
            description=workflow.description,  # type: ignore[attr-defined]
            status=workflow.status,  # type: ignore[attr-defined]
            graph=WorkflowGraph.model_validate(workflow.graph_json or {"nodes": [], "edges": []}),  # type: ignore[attr-defined]
            compiled_graph=workflow.compiled_graph or {},  # type: ignore[attr-defined]
            settings=workflow.settings or {},  # type: ignore[attr-defined]
            created_by=workflow.created_by,  # type: ignore[attr-defined]
            created_at=workflow.created_at,  # type: ignore[attr-defined]
            updated_at=workflow.updated_at,  # type: ignore[attr-defined]
        )

    model_config = ConfigDict(from_attributes=True)
