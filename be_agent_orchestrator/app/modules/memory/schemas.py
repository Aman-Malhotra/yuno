"""Memory module — response shapes for the API + internal callers.

These types describe what the mem0 backend hands us back. We keep them
as plain Pydantic models so the router can serialize them without ever
exposing the raw mem0 SDK shapes (which churn between releases).
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MemoryEntry(BaseModel):
    """One long-term memory row as returned by mem0.

    `id` is mem0's internal UUID. `memory` is the extracted fact /
    preference / summary string. `metadata` carries whatever we stamped at
    write time — for Telegram that's `{username, chat_id, agent_id,
    workflow_id}`.
    """

    id: str
    memory: str
    user_id: str | None = None
    agent_id: str | None = None
    hash: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float | None = Field(
        default=None,
        description="Cosine similarity when returned from a `search` call. Null for `get_all`.",
    )
    categories: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(extra="ignore")


class MemoryListResponse(BaseModel):
    items: list[MemoryEntry]
    total: int


class GraphNode(BaseModel):
    """One entity in the relation graph (a person, place, preference, …)."""

    id: str
    label: str = Field(description="Display name shown on the node.")
    type: str | None = Field(default=None, description="Entity type, when mem0 classifies it.")


class GraphEdge(BaseModel):
    """One relation between two entities."""

    source: str = Field(description="Source node id.")
    target: str = Field(description="Target node id.")
    label: str = Field(description="Relation type, e.g. `lives_in`.")


class MemoryGraph(BaseModel):
    """Graph projection of long-term memories for a user id.

    Comes from mem0's neo4j graph_store; empty arrays if graph memory is
    disabled or no relations have been extracted yet.
    """

    nodes: list[GraphNode]
    edges: list[GraphEdge]
