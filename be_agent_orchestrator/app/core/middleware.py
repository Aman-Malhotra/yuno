import json
import time
import uuid
from typing import Any

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.config import settings

log = structlog.get_logger("http")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Bind a request id (header or fresh UUID) to log context + echo it back."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        response: Response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response


# ──────────────────────────────────────────────────────────────────────
# Access log
# ──────────────────────────────────────────────────────────────────────

_SKIP_BODY_PATHS = {"/openapi.json", "/docs", "/redoc"}
_REDACT_HEADERS = {"authorization", "cookie", "set-cookie", "x-api-key"}

# Any JSON key matching these names is replaced with "***" before logging.
# Covers token responses (login/signup/refresh) and password fields on requests.
_REDACT_KEYS = {
    "access_token",
    "refresh_token",
    "token",
    "id_token",
    "password",
    "hashed_password",
    "secret",
    "api_key",
}


def _redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: ("***" if k.lower() in _REDACT_KEYS else _redact_value(v)) for k, v in value.items()
        }
    if isinstance(value, list):
        return [_redact_value(v) for v in value]
    return value


def _safe_body_for_log(data: bytes, limit: int) -> str:
    """Best-effort: parse as JSON, redact sensitive keys, re-serialize.

    Falls back to truncated raw text if the body isn't JSON.
    """

    try:
        parsed = json.loads(data)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _truncate(data, limit)

    redacted = _redact_value(parsed)
    text = json.dumps(redacted, separators=(",", ":"))
    return text if len(text) <= limit else text[:limit] + f"…<+{len(text) - limit}c>"


def _truncate(data: bytes, limit: int) -> str:
    if len(data) <= limit:
        return data.decode("utf-8", errors="replace")
    return data[:limit].decode("utf-8", errors="replace") + f"…<+{len(data) - limit}B>"


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


class AccessLogMiddleware(BaseHTTPMiddleware):
    """One structured log line per request.

    Always logs: method, path, status, duration_ms, client ip, request id.
    When ``settings.log_http_bodies`` is true: also logs the request body
    (truncated to ``settings.log_max_body_bytes``, ``Authorization`` redacted
    in headers). Response bodies are never logged — only the status code.
    Off by default — turn on in ``.env`` only when debugging.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        start = time.perf_counter()

        request_body: bytes = b""
        if settings.log_http_bodies and request.url.path not in _SKIP_BODY_PATHS:
            request_body = await request.body()

            # Re-inject the consumed body so the route handler can read it.
            async def _replay_body() -> dict[str, object]:
                return {"type": "http.request", "body": request_body, "more_body": False}

            request._receive = _replay_body

        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        log_fields: dict[str, object] = {
            "client_ip": _client_ip(request),
            "status": response.status_code,
            "duration_ms": duration_ms,
            "query": request.url.query,
        }

        if settings.log_http_bodies and request.url.path not in _SKIP_BODY_PATHS:
            log_fields["request_headers"] = {
                k: ("***" if k.lower() in _REDACT_HEADERS else v)
                for k, v in request.headers.items()
            }
            if request_body:
                log_fields["request_body"] = _safe_body_for_log(
                    request_body, settings.log_max_body_bytes
                )

        log.info("http.request", **log_fields)
        return response
