---
title: Modular Monolith, Not Microservices
impact: CRITICAL
impactDescription: One API + one worker keeps the assignment runnable in one command while still cleanly separating concerns
tags: architecture, monolith, processes
---

## Modular Monolith, Not Microservices

The backend ships as **two processes**: a FastAPI API service and an Arq worker service. They share the same codebase, the same `app/` package, the same models — they just run different entrypoints.

```txt
api service     -> REST, auth, WebSocket/SSE, webhooks
worker service  -> LangGraph workflows + background jobs
postgres        -> durable persistence (shared)
redis           -> queue + pub/sub (shared)
```

### Why

- The challenge must run with a **single command** (`docker compose up --build`)
- Microservices = more code, more network hops, more failure modes, zero benefit at this scale
- Splitting API and worker is still required: long workflow runs cannot block the request loop

### Bad — premature microservice split

```txt
# ❌ Five services for one assignment
agent-service/
workflow-service/
runtime-service/
channel-service/
gateway/
```

```python
# ❌ HTTP call from API to "runtime service"
async def start_run(payload):
    async with httpx.AsyncClient() as client:
        await client.post("http://runtime-service/run", json=payload)
```

### Bad — running workflows inside the request

```python
# ❌ Blocks the request for 30s+, breaks under load
@router.post("/workflows/{wid}/run")
async def run_workflow(wid: str):
    result = await langgraph_runtime.execute(wid)   # long-running
    return result
```

### Good — API enqueues, worker executes

```python
# app/api/v1/workflows.py
@router.post("/workflows/{workflow_id}/run", response_model=RunResponse)
async def run_workflow(
    workflow_id: str,
    payload: RunInput,
    current_user: User = Depends(get_current_user),
    service: RunService = Depends(get_run_service),
):
    run = await service.create_run(workflow_id, current_user.id, payload)
    await service.enqueue(run.id)
    return run
```

```python
# app/worker/jobs.py
async def execute_workflow_job(ctx, run_id: str) -> None:
    runtime = build_runtime(ctx)
    await runtime.execute_run(run_id)
```

### Process diagram

```txt
                  ┌────────────┐
   HTTP/WS ─────► │ api (8000) │ ──► Postgres
                  └─────┬──────┘
                        │ enqueue job
                        ▼
                      Redis ──► pub/sub events ──► WS clients
                        ▲
                        │ subscribe + pull jobs
                  ┌─────┴──────┐
                  │   worker   │ ──► Postgres
                  └────────────┘ ──► LLM providers + tools
```

See: [[arch-project-structure]], [[worker-job-boundary]], [[ops-docker-compose]], [[avoid-overengineering]]
