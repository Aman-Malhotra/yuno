---
title: API Enqueues, Worker Executes
impact: HIGH
impactDescription: Running a workflow inside a request handler ties up an HTTP worker for minutes; under load the API dies
tags: worker, queue, boundary
---

## API Enqueues, Worker Executes

The API never executes a workflow or processes a channel message synchronously. It writes the durable record to Postgres, enqueues a job, and returns immediately.

### Pattern

```python
# app/modules/runs/service.py
class RunService:
    def __init__(self, repo: RunRepository, events: RunEventRepository, arq_pool):
        self.repo = repo
        self.events = events
        self.arq_pool = arq_pool

    async def create_and_enqueue(
        self, workflow_id: str, user_id: str, input_data: dict
    ) -> WorkflowRun:
        run = await self.repo.create(
            workflow_id=workflow_id,
            user_id=user_id,
            input=input_data,
            status="queued",
        )
        await self.arq_pool.enqueue_job("execute_workflow_job", run.id)
        return run
```

### Wiring the Arq pool into the API

```python
# app/core/lifespan.py
from contextlib import asynccontextmanager
from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import settings


@asynccontextmanager
async def lifespan(app):
    app.state.arq_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    try:
        yield
    finally:
        await app.state.arq_pool.aclose()
```

```python
# app/api/deps.py
from fastapi import Request

def get_arq_pool(request: Request):
    return request.app.state.arq_pool


async def get_run_service(
    repo: RunRepository = Depends(get_run_repository),
    events: RunEventRepository = Depends(get_run_event_repository),
    arq_pool = Depends(get_arq_pool),
) -> RunService:
    return RunService(repo, events, arq_pool)
```

### Router

```python
# app/modules/workflows/router.py
@router.post("/{workflow_id}/run", response_model=RunResponse, status_code=202)
async def run_workflow(
    workflow_id: str,
    payload: RunInput,
    current_user: User = Depends(get_current_user),
    run_service: RunService = Depends(get_run_service),
):
    run = await run_service.create_and_enqueue(
        workflow_id=workflow_id,
        user_id=current_user.id,
        input_data=payload.model_dump(),
    )
    return RunResponse.model_validate(run)
```

The response is `202 Accepted` with the run id; the client connects to the WebSocket `/api/v1/monitoring/runs/{run_id}` for live progress.

### Channel webhook follows the same pattern

```python
# app/modules/channels/webhooks/telegram.py
@router.post("/telegram/webhook")
async def telegram_webhook(
    update: dict,
    channel_service: ChannelService = Depends(get_channel_service),
    arq_pool = Depends(get_arq_pool),
):
    # Validate signature, store the incoming message row
    incoming = await channel_service.record_incoming(update)
    # Hand off to the worker — never call the LLM in this handler
    await arq_pool.enqueue_job("process_channel_message_job", incoming.id)
    return {"ok": True}
```

### Bad — executing inline

```python
# ❌ 30s LLM call blocks one HTTP worker per request
@router.post("/{workflow_id}/run")
async def run_workflow(workflow_id: str, ...):
    result = await runtime.execute(workflow_id)
    return result
```

### Bad — `BackgroundTasks` for long jobs

```python
# ❌ Runs in the same process; dies on reload; not retried; not observable
@router.post("/{workflow_id}/run")
async def run_workflow(..., bg: BackgroundTasks):
    bg.add_task(runtime.execute, workflow_id)
```

`BackgroundTasks` is fine for "send a webhook ack after responding", not for multi-minute workflow runs.

### Rules

- Any operation that calls an LLM, a tool that hits the network, or a long-running workflow goes via Arq
- The API only writes durable state + enqueues — never executes
- Webhook handlers (Telegram/Slack) acknowledge fast (<200ms) and enqueue
- Return `202 Accepted` for enqueued operations; the client gets the work id and subscribes for updates

See: [[worker-arq-setup]], [[arch-modular-monolith]], [[channel-webhook-and-providers]]
