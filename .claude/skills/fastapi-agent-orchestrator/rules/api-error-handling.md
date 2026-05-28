---
title: Typed App Exceptions + Global Handler
impact: CRITICAL
impactDescription: Services raise domain errors; one handler maps them to HTTP — keeps services framework-agnostic
tags: api, errors, exception-handling
---

## Typed App Exceptions + Global Handler

Services raise typed app exceptions. A single global handler maps them to HTTP responses.

### Exception hierarchy

```python
# app/core/errors.py
from typing import Any


class AppError(Exception):
    code: str = "internal_error"
    http_status: int = 500

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


class NotFoundError(AppError):
    http_status = 404


class PermissionDeniedError(AppError):
    http_status = 403


class ValidationError(AppError):
    http_status = 422


class ConflictError(AppError):
    http_status = 409


class UnauthorizedError(AppError):
    http_status = 401


class ExternalServiceError(AppError):
    http_status = 502
```

### Global handler

```python
# app/core/errors.py (continued)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import structlog

log = structlog.get_logger()


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content={
                "error": {
                    "code": exc.code.upper(),
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid request payload",
                    "details": {"errors": exc.errors()},
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled_exception", path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Internal server error",
                    "details": {},
                }
            },
        )
```

Wire it once in `create_app()`:

```python
# app/main.py
register_exception_handlers(app)
```

### Bad — services raising HTTPException

```python
# ❌ Couples service to FastAPI; can't reuse from the worker
class AgentService:
    async def get(self, agent_id: str):
        agent = await self.repo.get_by_id(agent_id)
        if not agent:
            raise HTTPException(404, "agent not found")
```

### Good — services raise domain errors

```python
# ✅ Worker can call this too without importing FastAPI
class AgentService:
    async def get_agent(self, user_id: str, agent_id: str) -> Agent:
        agent = await self.repository.get_by_id(agent_id)
        if agent is None:
            raise NotFoundError("agent_not_found", f"agent {agent_id} not found")
        if agent.user_id != user_id:
            raise PermissionDeniedError("agent_forbidden", "not your agent")
        return agent
```

### Error code conventions

- Snake-case at raise site: `agent_not_found`
- Upper-snake on the wire: `AGENT_NOT_FOUND`
- Stable strings — the React client switches on them
- Include `details` for anything the UI should render (field errors, run id, etc.)

See: [[arch-layering-separation]], [[api-response-shapes]], [[ops-logging-and-request-id]]
