import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI
from redis.asyncio import Redis

from app.core.config import settings

log = structlog.get_logger("lifespan")


def _warm_memory_client() -> None:
    """Force the mem0 singleton to initialize AND exercise its embedder.

    First-time init pulls the sentence-transformers MiniLM model from
    HuggingFace (~90 MB) and opens the pgvector + Neo4j connection pools.
    We do it eagerly at startup so the first user request that hits the
    Memories tab doesn't wait for that download.

    Note: ``Memory.from_config`` does NOT load the embedder — that's
    lazy-loaded at add/search time. We follow up with a dry search so a
    missing ``sentence_transformers`` package surfaces here at boot
    instead of silently no-oping every memory call in production.

    Failures are downgraded to a warning — memory is best-effort, the rest
    of the app must still boot. mem0 will retry on the next call.
    """

    try:
        from app.modules.memory.service import _client  # noqa: PLC0415

        client = _client()
        # Dry search forces the embedder to load. The user_id is bogus
        # on purpose — we just want the model path exercised. Empty result
        # is fine; any exception here is the real signal.
        # mem0 ≥ 0.1.108 requires scopes under `filters=` and REJECTS
        # the same key at top-level — pass only via filters.
        client.search(
            query="warmup",
            filters={"user_id": "__warmup__"},
            limit=1,
        )
        log.info("memory.warmup.ok")
    except Exception as err:  # noqa: BLE001
        log.exception(
            "memory.warmup.failed",
            error_type=type(err).__name__,
            error=str(err),
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.arq_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=False)

    # Off-thread because the warmup is heavy + sync (HuggingFace download,
    # Neo4j handshake). We don't await it — the app boots immediately and
    # the first memory call blocks only if init hasn't finished yet.
    asyncio.create_task(asyncio.to_thread(_warm_memory_client))

    try:
        yield
    finally:
        await app.state.arq_pool.aclose()
        await app.state.redis.aclose()


async def worker_startup(ctx: dict[str, Any]) -> None:
    # Force every module's models to register against Base.metadata so
    # cross-table FKs (workflow_runs → workspaces/workflows/users/agents)
    # resolve. Without this the worker only knows about whatever a job
    # function happens to import directly, and SQLAlchemy raises
    # NoReferencedTableError on the first commit.
    import app.db.models  # noqa: F401

    # Same warmup on the worker — the runtime agent node is what actually
    # writes memories, so the worker needs the client ready too.
    await asyncio.to_thread(_warm_memory_client)

    ctx["redis"] = Redis.from_url(settings.redis_url, decode_responses=False)


async def worker_shutdown(ctx: dict[str, Any]) -> None:
    redis = ctx.get("redis")
    if redis is not None:
        await redis.aclose()
