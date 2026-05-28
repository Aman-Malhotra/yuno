from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PageResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class ErrorDetail(BaseModel):
    """The `error` field of every non-2xx response.

    Mirrors what ``app.core.errors.register_exception_handlers`` emits, so
    the OpenAPI schema matches the real wire format byte-for-byte.
    """

    code: str = Field(description="Stable upper-snake error code. Switch on this in the UI.")
    message: str = Field(description="Human-readable summary; safe to surface to the user.")
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured per-error data (validation errors, conflict keys, etc).",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "code": "AGENT_NOT_FOUND",
                    "message": "Agent not found",
                    "details": {"agent_id": "01HZ..."},
                }
            ]
        }
    )


class ErrorEnvelope(BaseModel):
    """Top-level error response shape returned by every error path."""

    error: ErrorDetail

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Invalid request payload",
                        "details": {
                            "errors": [{"loc": ["body", "email"], "msg": "field required"}]
                        },
                    }
                }
            ]
        }
    )
