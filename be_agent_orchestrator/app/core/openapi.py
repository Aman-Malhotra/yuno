"""OpenAPI standard for the Yuno backend.

Every route declares:

- ``response_model=`` — the success Pydantic schema
- ``status_code=`` — explicit, not implicit 200
- ``summary=`` and a ``description=`` (or a docstring fallback)
- ``tags=`` from one canonical list (avoid free-text tag drift)
- ``responses=`` merged from ``COMMON_ERROR_RESPONSES`` plus per-route extras
- ``operation_id=`` in ``<tag>_<verb>_<noun>`` form for codegen-friendly names

A single bearer scheme (``BearerAuth``) is declared globally; routes that
need it set ``dependencies=[Depends(get_current_user)]`` which auto-adds
the security requirement. Public routes (login, refresh, health) skip it.
"""

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.core.config import settings
from app.core.schemas import ErrorEnvelope

# ──────────────────────────────────────────────────────────────────────
# Tag metadata — single source of truth for grouping in /docs
# ──────────────────────────────────────────────────────────────────────

TAGS_METADATA: list[dict[str, str]] = [
    {"name": "meta", "description": "Health, version, and OpenAPI utility endpoints."},
    {"name": "auth", "description": "Login, refresh, logout, and current-user lookup."},
    {"name": "users", "description": "User account management."},
    {"name": "agents", "description": "Agent CRUD and per-agent test runs."},
    {"name": "workflows", "description": "Workflow CRUD, validation, templates, runs."},
    {"name": "runs", "description": "Workflow run history, cancel, events, messages."},
    {"name": "messages", "description": "Inter-agent and channel message history."},
    {
        "name": "tools",
        "description": (
            "Tool registry — CRUD on workspace-scoped tools, the built-in "
            "handler catalog, versioning, the test console, execution + log "
            "history, human-approval queue, and per-agent tool permissions."
        ),
    },
    {"name": "llm-providers", "description": "Configured LLM providers and their models."},
    {"name": "channels", "description": "External channel connect/disconnect + webhooks."},
    {"name": "monitoring", "description": "Realtime WebSocket stream for run events."},
]


# ──────────────────────────────────────────────────────────────────────
# Reusable error responses for the `responses=` argument on routes
# ──────────────────────────────────────────────────────────────────────


def _error_response(description: str) -> dict[str, Any]:
    return {"model": ErrorEnvelope, "description": description}


COMMON_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: _error_response("Bad request — malformed input"),
    401: _error_response("Missing or invalid bearer token"),
    403: _error_response("Authenticated but not allowed"),
    404: _error_response("Resource not found"),
    409: _error_response("Conflict with existing state"),
    422: _error_response("Validation error on request payload"),
    500: _error_response("Internal server error"),
}


def auth_required_responses(*extra_codes: int) -> dict[int | str, dict[str, Any]]:
    """Standard error responses for an authenticated, non-mutating route."""

    return {code: COMMON_ERROR_RESPONSES[code] for code in (401, 403, 422, 500, *extra_codes)}


def public_responses(*extra_codes: int) -> dict[int | str, dict[str, Any]]:
    """Standard error responses for a public (no-auth) route."""

    return {code: COMMON_ERROR_RESPONSES[code] for code in (400, 422, 500, *extra_codes)}


# ──────────────────────────────────────────────────────────────────────
# customize_openapi — single place to override the auto-generated schema
# ──────────────────────────────────────────────────────────────────────


_API_DESCRIPTION = """
Yuno AI Agent Orchestration Platform — backend API.

Stack: FastAPI · LangGraph · PostgreSQL · Redis · Arq.

**Auth.** All non-public endpoints require an `Authorization: Bearer <access_token>`
header. Obtain tokens via `POST /api/v1/auth/login` and rotate via
`POST /api/v1/auth/refresh`. The access token is valid for 12 hours; the
refresh token for 30 days.

**Error envelope.** Every non-2xx response is `{"error": {"code", "message", "details"}}`.
Switch on `code` in the frontend (it's stable); render `message` to the user;
inspect `details` for structured per-error data.
"""


def customize_openapi(app: FastAPI) -> None:
    """Install a memoized openapi() that adds info, servers, and BearerAuth."""

    def _build() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema

        schema = get_openapi(
            title=app.title,
            version="0.1.0",
            description=_API_DESCRIPTION,
            routes=app.routes,
            tags=TAGS_METADATA,
            servers=[
                {"url": "http://localhost:3001", "description": "Local dev"},
                {"url": "http://api:3001", "description": "Docker compose internal"},
            ],
        )

        components = schema.setdefault("components", {})
        security_schemes = components.setdefault("securitySchemes", {})
        security_schemes["BearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Paste your access token (without the `Bearer ` prefix).",
        }

        # Surface contact + license info for downstream codegen / docs portals.
        info = schema.setdefault("info", {})
        info["contact"] = {"name": "Yuno AI", "email": "engineering@yuno.ai"}
        info["license"] = {"name": "Proprietary"}
        info["x-environment"] = settings.environment

        app.openapi_schema = schema
        return schema

    app.openapi = _build  # type: ignore[method-assign]
