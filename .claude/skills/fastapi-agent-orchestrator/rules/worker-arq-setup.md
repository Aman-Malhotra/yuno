---
title: Arq Worker Setup
impact: HIGH
impactDescription: Workflow runs and channel webhook processing must not block API requests; Arq is the simplest async-native queue
tags: worker, arq, redis
---

## Arq Worker Setup

A single Arq worker process consumes jobs from Redis. Jobs are plain async functions.

### Layout

```txt
app/worker/
  arq_app.py       # WorkerSettings (Arq entrypoint)
  jobs.py          # async job functions
  schedules.py     # cron-style schedules
```

### `WorkerSettings`

```python
# app/worker/arq_app.py
from arq.connections import RedisSettings

from app.core.config import settings
from app.core.lifespan import worker_startup, worker_shutdown
from app.worker import jobs


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.redis_url)

    functions = [
        jobs.execute_workflow_job,
        jobs.process_channel_message_job,
        jobs.send_channel_message_job,
    ]

    on_startup = worker_startup
    on_shutdown = worker_shutdown

    max_jobs = 10
    job_timeout = 300        # 5 min hard cap per job
    keep_result = 3600       # keep result for 1h for debugging
    health_check_interval = 30
```

### Startup / shutdown hooks build shared state

```python
# app/core/lifespan.py
from redis.asyncio import Redis

from app.core.config import settings


async def worker_startup(ctx):
    ctx["redis"] = Redis.from_url(settings.redis_url, decode_responses=False)


async def worker_shutdown(ctx):
    await ctx["redis"].aclose()
```

`ctx["redis"]` is then available to every job — use it for pub/sub emission inside the runtime. The DB session is opened per-job (see [[db-session-lifecycle]]).

### Job example

```python
# app/worker/jobs.py
import structlog

from app.db.session import AsyncSessionLocal
from app.modules.runs.repository import RunRepository, RunEventRepository
from app.modules.runs.service import RunService
from app.modules.runtime.langgraph_runtime import LangGraphRuntime

log = structlog.get_logger()


async def execute_workflow_job(ctx, run_id: str) -> None:
    log.info("workflow.run.start", run_id=run_id)
    async with AsyncSessionLocal() as db:
        runs = RunRepository(db)
        events = RunEventRepository(db)
        run_service = RunService(runs, events)
        runtime = LangGraphRuntime(run_service, events, ctx["redis"])
        try:
            await runtime.execute_run(run_id)
        except Exception:
            log.exception("workflow.run.failed", run_id=run_id)
            await run_service.mark_failed(run_id)
            raise
```

### Running it

```bash
uv run arq app.worker.arq_app.WorkerSettings
```

In Docker Compose, the worker is a separate service with the same image and a different command. See [[ops-docker-compose]].

### Bad — Celery for this scale

```toml
# ❌ Heavier setup, sync defaults, more config
dependencies = ["celery", "kombu", "billiard"]
```

### Bad — background tasks in the API

```python
# ❌ FastAPI BackgroundTasks die with the request; lose state on reload
@router.post("/runs/{rid}/start")
async def start(rid: str, bg: BackgroundTasks):
    bg.add_task(execute_run, rid)
```

### Rules

- One `WorkerSettings` class — declared in `app/worker/arq_app.py`
- Every queued function is listed in `WorkerSettings.functions`
- `on_startup` builds shared resources (redis client); `on_shutdown` closes them
- DB sessions opened **inside** each job, never on the `ctx`
- `job_timeout` set explicitly (default is forever — bad)
- Logging in jobs always includes `run_id` / `channel_id` for correlation

See: [[worker-job-boundary]], [[realtime-websocket-redis-pubsub]], [[ops-docker-compose]]
