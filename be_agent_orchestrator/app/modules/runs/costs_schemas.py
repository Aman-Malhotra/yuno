"""Response shapes for the per-agent token-cost view."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgentCostRow(BaseModel):
    """One row per agent in the workspace's cost roll-up.

    `input_tokens` + `output_tokens` are summed across every
    `node.completed` event that this agent emitted. `run_count` is the
    number of agent turns (not workflow runs) — one turn = one LLM
    completion round-trip in our executor.
    """

    agent_id: UUID
    name: str
    slug: str = Field(description="Agent slug; empty when the agent was soft-deleted.")
    model_provider: str
    model_name: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    run_count: int
    last_seen_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CostsResponse(BaseModel):
    """Workspace-wide totals + per-agent breakdown.

    Totals sum across `items` so the UI can render percentages without a
    second pass.
    """

    items: list[AgentCostRow]
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
