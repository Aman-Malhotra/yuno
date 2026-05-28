---
title: Structlog + Request-ID Middleware
impact: MEDIUM
impactDescription: Structured logs with a request id make multi-step flows (API → worker → LLM → Redis → WS) debuggable
tags: ops, logging, observability
---

## Structlog + Request-ID Middleware

Every log line is JSON-ish key/value, with a `request_id` tag that follows the request through services and into the worker.

### Configure structlog

```python
# app/core/logging.py
import logging
import structlog

from app.core.config import settings


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO if settings.environment != "local" else logging.DEBUG,
        format="%(message)s",
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

Call once in `create_app()` before any router include.

### Request-ID middleware

```python
# app/core/middleware.py
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import structlog


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response
```

Wire it once:

```python
# app/main.py
app.add_middleware(RequestIdMiddleware)
```

### Use it everywhere

```python
import structlog

log = structlog.get_logger()


class AgentService:
    async def create_agent(self, user_id: str, payload: CreateAgentRequest) -> Agent:
        log.info("agent.create", user_id=user_id, model=payload.model_provider)
        ...
```

Output:

```json
{"timestamp": "2026-05-23T20:01:13Z", "level": "info", "event": "agent.create",
 "request_id": "f8b…", "user_id": "u_…", "model": "openai", "method": "POST",
 "path": "/api/v1/agents/"}
```

### Propagating the request id into the worker

When the API enqueues a job, pass the request id as a job kwarg:

```python
await arq_pool.enqueue_job(
    "execute_workflow_job",
    run_id,
    request_id=structlog.contextvars.get_contextvars().get("request_id"),
)
```

Worker job rebinds it:

```python
async def execute_workflow_job(ctx, run_id: str, request_id: str | None = None) -> None:
    structlog.contextvars.clear_contextvars()
    if request_id:
        structlog.contextvars.bind_contextvars(request_id=request_id, run_id=run_id)
    ...
```

Now one `request_id` traces a click in the UI → API → worker → LLM call.

### Bad — `print()` for debugging

```python
# ❌ Unstructured, lost in production
print(f"creating agent {payload.name}")
```

### Bad — logging the JWT or full request body

```python
# ❌ PII / credential leak
log.info("login", body=request_body)
```

Log identifiers (user_id, agent_id, run_id), never raw payloads or tokens.

### What to log

- **info** — state transitions (`run.queued`, `run.started`, `run.completed`, `webhook.received`)
- **warning** — recoverable issues (`llm.retry`, `tool.timeout`)
- **error** — caught exceptions before re-raise
- **exception** — unhandled — only the global handler logs at this level

### Rules

- One logging setup in `core/logging.py`, called once in `create_app()` and in worker `on_startup`
- One middleware binds `request_id`, `method`, `path` on every request
- Worker jobs accept `request_id` kwarg + rebind it
- Never log raw tokens, raw passwords, raw LLM prompts, or full request/response bodies
- Log identifiers, not payloads

See: [[api-error-handling]], [[worker-arq-setup]], [[ops-settings-pydantic]]
