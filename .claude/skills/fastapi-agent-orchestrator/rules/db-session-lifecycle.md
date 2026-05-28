---
title: Session per Request, Session per Job
impact: CRITICAL
impactDescription: A leaked session = leaked connection = the whole pool stalls under load
tags: db, sessions, lifecycle
---

## Session per Request, Session per Job

Every HTTP request gets a fresh `AsyncSession`, scoped by the FastAPI dependency. Every worker job opens its own session inside a context manager and closes it before returning.

### API side

```python
# app/db/session.py
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

Routes consume it via the repository/service chain (see [[api-dependency-injection]]). FastAPI calls the generator's `__aexit__` when the response is sent — the session closes and the connection returns to the pool.

### Worker side

```python
# app/worker/jobs.py
from app.db.session import AsyncSessionLocal


async def execute_workflow_job(ctx, run_id: str) -> None:
    async with AsyncSessionLocal() as db:
        # build repositories + services with this session
        run_service = RunService(RunRepository(db), ...)
        await run_service.mark_started(run_id)
        # ... do work ...
        await run_service.mark_completed(run_id)
```

Long-running jobs that hold a session for many seconds are fine for this assignment scale. If a job becomes very long, open and close multiple short-lived sessions instead.

### Transactions

By default `AsyncSession` operates in "begin once, commit when you say so". Two patterns:

**Per-write commit (default repository style):**

```python
async def create(self, **kwargs) -> Agent:
    agent = Agent(**kwargs)
    self.db.add(agent)
    await self.db.commit()
    await self.db.refresh(agent)
    return agent
```

**Multi-step transaction (use `session.begin()`):**

```python
async with self.db.begin():
    self.db.add(run)
    self.db.add(initial_event)
    # commit happens automatically at __aexit__
```

Pick one style per write path. Don't mix `begin()` with manual `commit()` in the same call.

### Bad — global session

```python
# ❌ Shared across requests, will corrupt state under concurrency
session = AsyncSessionLocal()

@router.get("/agents")
async def list_agents():
    return await session.execute(select(Agent))
```

### Bad — forgetting to close in worker

```python
# ❌ Connection never returns to the pool
async def job(ctx, run_id: str):
    db = AsyncSessionLocal()
    await db.execute(...)
    # missing `await db.close()` or context manager
```

### Bad — passing the session through many layers

Don't snake the session through 5 function args. Build the repository once at the boundary (request or job), and pass *the repository* down.

### Rollback on error

The `async with AsyncSessionLocal()` context manager already calls `rollback()` on exception. You don't need to add manual try/except for rollback unless you want to swallow a specific error.

### Rules

- API: session lifecycle owned by `get_db_session()`, scoped per request
- Worker: session lifecycle owned by `async with AsyncSessionLocal()` inside each job
- One session per logical unit of work; never shared across requests/jobs
- Never store an `AsyncSession` on a module-level singleton or class attribute that outlives a request/job

See: [[db-async-sqlalchemy]], [[api-dependency-injection]], [[worker-job-boundary]]
