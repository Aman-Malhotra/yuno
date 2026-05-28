from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

RunStatus = Literal["queued", "running", "waiting", "completed", "failed", "cancelled"]
TriggerType = Literal["manual", "schedule", "channel", "api", "test"]
RunNodeStatus = Literal[
    "queued", "running", "waiting", "completed", "failed", "skipped", "cancelled"
]


class RunSummary(BaseModel):
    id: UUID
    workspace_id: UUID
    workflow_id: UUID | None = None
    status: RunStatus
    trigger_type: TriggerType
    trigger_source: str | None = None
    error_message: str | None = None
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RunNodeView(BaseModel):
    id: UUID
    node_id: str = Field(description="Graph node id (e.g. `intake`, `triage`).")
    node_type: str
    node_label: str | None = None
    agent_id: UUID | None = None
    tool_id: UUID | None = None
    status: RunNodeStatus
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    error_details: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class RunEventView(BaseModel):
    id: UUID
    sequence_number: int
    event_type: str
    node_id: str | None = None
    agent_id: UUID | None = None
    tool_id: UUID | None = None
    message: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RunDetail(RunSummary):
    """Full run with per-step rows and the event stream.

    `nodes` is the canonical "what happened at each step" view (in/out
    payloads, status, timing). `events` is the granular append-only log —
    same data sliced finer (started/completed/tool.called/branch.matched)
    for live UIs and audit trails.
    """

    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    nodes: list[RunNodeView] = Field(default_factory=list)
    events: list[RunEventView] = Field(default_factory=list)


class RunAcknowledgement(BaseModel):
    """Returned by the public webhook ingress.

    202 Accepted — the run is queued, not executed.
    """

    run_id: UUID
    status: RunStatus
    accepted_at: datetime
    input: dict[str, Any] = Field(default_factory=dict)
