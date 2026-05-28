"""Long-term memory service — thin wrapper around mem0 OSS.

Design notes
------------
- One process-wide ``Memory`` client. mem0 holds a pgvector connection
  pool + a Neo4j driver; spinning them up per call would be wasteful.
- mem0 is sync. FastAPI handlers + runtime nodes are async. Every public
  method here goes through ``asyncio.to_thread`` so we never block the
  event loop on a vector query.
- mem0 returns raw dicts whose shape varies by SDK version. We normalise
  into ``MemoryEntry`` / ``MemoryGraph`` so callers depend on our types,
  not theirs.
- All long-term writes carry ``user_id`` = the channel-side stable id
  (Telegram numeric user id). ``metadata.username`` is the friendly
  handle and is searchable. We never use the username as the primary id
  because Telegram lets users change it.
"""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any

import structlog

from app.core.config import settings
from app.modules.memory.schemas import (
    GraphEdge,
    GraphNode,
    MemoryEntry,
    MemoryGraph,
)

log = structlog.get_logger("memory")


# ──────────────────────────────────────────────────────────────────────
# Client construction
# ──────────────────────────────────────────────────────────────────────


def _parse_database_url() -> dict[str, Any]:
    """Pull the pieces mem0's pgvector backend wants out of DATABASE_URL.

    mem0's pgvector store takes ``host``, ``port``, ``user``, ``password``,
    ``dbname`` separately — not a URL. ``settings.database_url`` is the
    SQLAlchemy URL (``postgresql+asyncpg://…``); we strip the driver
    suffix because mem0 uses sync psycopg under the hood.
    """

    from urllib.parse import urlparse

    raw = settings.database_url.replace("+asyncpg", "").replace("+psycopg", "")
    parsed = urlparse(raw)
    return {
        "user": parsed.username or "",
        "password": parsed.password or "",
        "host": parsed.hostname or "",
        "port": parsed.port or 5432,
        "dbname": (parsed.path or "/").lstrip("/"),
    }


def _build_config() -> dict[str, Any]:
    """Compose the dict mem0's ``Memory.from_config`` expects."""

    if not settings.openrouter_api_key_memory:
        raise RuntimeError(
            "OPENROUTER_API_KEY_MEMORY is not set — long-term memory is unavailable. "
            "Set it in .env or disable `memory_config.enable_long_term` on agents.",
        )

    pg = _parse_database_url()
    embedder_cfg: dict[str, Any] = {"model": settings.mem0_embedder_model}
    if settings.mem0_embedder_api_key:
        embedder_cfg["api_key"] = settings.mem0_embedder_api_key

    # MiniLM-L6-v2 = 384, OpenAI text-embedding-3-small = 1536. mem0
    # defaults the pgvector column to 1536 if not told otherwise; insert
    # then fails when the embedder ships a 384-vec into a vector(1536)
    # column. Keep these in lockstep — if the embedder model changes,
    # update this dim AND drop the old `agent_memories_mem0` table so
    # mem0 recreates it with the correct dimension.
    embedding_dims = 384 if settings.mem0_embedder_provider == "huggingface" else 1536
    embedder_cfg["embedding_dims"] = embedding_dims

    return {
        "llm": {
            # mem0 has no native `openrouter` provider, but its `openai`
            # provider accepts a custom `openai_base_url`. Point that at
            # OpenRouter's OpenAI-compatible endpoint and we're done —
            # any OpenRouter model id works as the `model` value.
            "provider": "openai",
            "config": {
                "api_key": settings.openrouter_api_key_memory,
                "model": settings.mem0_llm_model,
                "openai_base_url": settings.mem0_openrouter_base_url,
            },
        },
        "embedder": {
            "provider": settings.mem0_embedder_provider,
            "config": embedder_cfg,
        },
        "vector_store": {
            "provider": "pgvector",
            "config": {
                **pg,
                # mem0 creates this table itself; we just name it.
                "collection_name": "agent_memories_mem0",
                "embedding_model_dims": embedding_dims,
            },
        },
        "graph_store": {
            "provider": "neo4j",
            "config": {
                "url": settings.neo4j_url,
                "username": settings.neo4j_user,
                "password": settings.neo4j_password,
            },
        },
        "version": "v1.1",
    }


@lru_cache(maxsize=1)
def _client() -> Any:
    """Lazy singleton. Importing ``mem0`` is heavy (pulls torch when the
    huggingface embedder is selected), so we defer it until first use."""

    from mem0 import Memory

    config = _build_config()
    log.info(
        "memory.client.init",
        llm_model=config["llm"]["config"]["model"],
        embedder_provider=config["embedder"]["provider"],
        vector_store="pgvector",
        graph_store="neo4j",
    )
    return Memory.from_config(config)


# ──────────────────────────────────────────────────────────────────────
# Result normalization
# ──────────────────────────────────────────────────────────────────────


def _normalise_entry(raw: dict[str, Any]) -> MemoryEntry:
    """mem0's row keys drift between versions — flatten to MemoryEntry."""

    return MemoryEntry(
        id=str(raw.get("id") or ""),
        memory=str(raw.get("memory") or raw.get("text") or ""),
        user_id=str(raw["user_id"]) if raw.get("user_id") is not None else None,
        agent_id=str(raw["agent_id"]) if raw.get("agent_id") is not None else None,
        hash=raw.get("hash"),
        metadata=raw.get("metadata") or {},
        score=raw.get("score"),
        categories=raw.get("categories") or [],
        created_at=raw.get("created_at"),
        updated_at=raw.get("updated_at"),
    )


def _entries(results: Any) -> list[MemoryEntry]:
    """Unwrap mem0's variable return shapes into a flat list of entries.

    mem0 1.x returns either a list of dicts, or ``{"results": [...]}``,
    or ``{"results": [...], "relations": [...]}``. Handle all three.
    """

    if isinstance(results, dict):
        raw_list = results.get("results") or []
    elif isinstance(results, list):
        raw_list = results
    else:
        raw_list = []
    return [_normalise_entry(r) for r in raw_list if isinstance(r, dict)]


def _relations(results: Any) -> list[dict[str, Any]]:
    if isinstance(results, dict):
        rel = results.get("relations") or []
        return [r for r in rel if isinstance(r, dict)]
    return []


# ──────────────────────────────────────────────────────────────────────
# Public surface
# ──────────────────────────────────────────────────────────────────────


class MemoryService:
    """Façade used by routers + runtime. Holds no state; all calls go to
    the mem0 singleton via ``asyncio.to_thread`` to keep the event loop free.
    """

    async def add(
        self,
        messages: list[dict[str, str]],
        *,
        user_id: str,
        agent_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Persist a turn (or list of turns) into long-term memory.

        mem0 runs its extractor LLM (Groq) to distil facts before storing
        — so a chatty round-trip can produce 0..N memory rows. We don't
        return them here; callers that need the new rows should re-fetch.
        """

        def _run() -> None:
            _client().add(
                messages,
                user_id=user_id,
                agent_id=agent_id,
                metadata=metadata or {},
            )

        try:
            await asyncio.to_thread(_run)
        except Exception as err:  # noqa: BLE001 — never fail the run on a memory hiccup
            log.exception(
                "memory.add.failed",
                user_id=user_id,
                agent_id=agent_id,
                metadata=metadata,
                error_type=type(err).__name__,
                error=str(err),
            )

    async def search(
        self,
        query: str,
        *,
        user_id: str,
        limit: int = 5,
    ) -> list[MemoryEntry]:
        """Top-k semantic recall scoped to ``user_id``.

        mem0 ≥ 0.1.108 moved entity scopes into ``filters=`` and rejects
        the same key at the top level. We pass it only via filters.
        """

        def _run() -> Any:
            return _client().search(
                query=query,
                filters={"user_id": user_id},
                limit=limit,
            )

        try:
            raw = await asyncio.to_thread(_run)
        except Exception as err:  # noqa: BLE001
            log.exception(
                "memory.search.failed",
                user_id=user_id,
                query=query,
                limit=limit,
                error_type=type(err).__name__,
                error=str(err),
            )
            return []
        return _entries(raw)

    async def list_for_user(
        self,
        *,
        user_id: str,
        limit: int = 100,
    ) -> list[MemoryEntry]:
        """All long-term memories for a user id (no relevance filter)."""

        def _run() -> Any:
            return _client().get_all(
                filters={"user_id": user_id},
                limit=limit,
            )

        try:
            raw = await asyncio.to_thread(_run)
        except Exception as err:  # noqa: BLE001
            log.exception(
                "memory.list.failed",
                user_id=user_id,
                limit=limit,
                error_type=type(err).__name__,
                error=str(err),
            )
            return []
        return _entries(raw)

    async def graph_for_user(self, *, user_id: str) -> MemoryGraph:
        """Project the entity-relation graph mem0 built from this user's turns.

        Returns ``MemoryGraph(nodes=[], edges=[])`` when graph memory is
        disabled or empty — never raises so the UI can render a placeholder.
        """

        def _run() -> Any:
            return _client().get_all(
                filters={"user_id": user_id},
                limit=1000,
            )

        try:
            raw = await asyncio.to_thread(_run)
        except Exception as err:  # noqa: BLE001
            log.exception(
                "memory.graph.failed",
                user_id=user_id,
                error_type=type(err).__name__,
                error=str(err),
            )
            return MemoryGraph(nodes=[], edges=[])

        relations = _relations(raw)
        node_index: dict[str, GraphNode] = {}
        edges: list[GraphEdge] = []
        for rel in relations:
            src = str(rel.get("source") or "")
            tgt = str(rel.get("destination") or rel.get("target") or "")
            rel_type = str(rel.get("relationship") or rel.get("relation") or "related_to")
            if not src or not tgt:
                continue
            node_index.setdefault(src, GraphNode(id=src, label=src, type=rel.get("source_type")))
            node_index.setdefault(
                tgt, GraphNode(id=tgt, label=tgt, type=rel.get("destination_type"))
            )
            edges.append(GraphEdge(source=src, target=tgt, label=rel_type))

        return MemoryGraph(nodes=list(node_index.values()), edges=edges)

    async def delete(self, memory_id: str) -> bool:
        """Delete a single memory row by mem0 id. Returns True on success."""

        def _run() -> None:
            _client().delete(memory_id=memory_id)

        try:
            await asyncio.to_thread(_run)
            return True
        except Exception as err:  # noqa: BLE001
            log.exception(
                "memory.delete.failed",
                memory_id=memory_id,
                error_type=type(err).__name__,
                error=str(err),
            )
            return False
