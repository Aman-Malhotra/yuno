from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ──────────────────────────────────────────────────────────────────────
# Requests
# ──────────────────────────────────────────────────────────────────────


class SetLLMCredentialsRequest(BaseModel):
    """Set or update credentials for a single LLM provider.

    Upsert semantics: if the user already has a row for this provider,
    the existing row's `credentials` JSONB is overwritten with the new
    payload (use full replacement, not deep-merge — clearer behavior).
    """

    api_key: str = Field(
        min_length=1,
        description="Provider API key (e.g. `sk-...`, `gsk_...`, `AIza...`).",
    )
    base_url: str | None = Field(
        default=None,
        description="Custom API base URL. Useful for OpenAI-compatible endpoints / Groq mirrors.",
    )
    organization: str | None = Field(
        default=None,
        description="OpenAI organization id, if applicable.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"api_key": "sk-proj-..."},
                {"api_key": "gsk_..."},
                {"api_key": "AIza..."},
            ]
        }
    )


# ──────────────────────────────────────────────────────────────────────
# Responses
# ──────────────────────────────────────────────────────────────────────


class LLMCredentialStatus(BaseModel):
    """Status of one provider's credential for the current user.

    Never echoes the `api_key`. Surfaces only the public fields the FE
    needs to render the settings card: provider, configured flag, the
    non-secret bits (base_url, organization), and timestamps.
    """

    provider: str
    is_configured: bool
    base_url: str | None = None
    organization: str | None = None
    updated_at: datetime | None = Field(
        default=None,
        description="When the credential was last set/updated. Null if unconfigured.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "provider": "openai",
                    "is_configured": True,
                    "base_url": None,
                    "organization": None,
                    "updated_at": "2026-05-24T08:15:30.000Z",
                },
                {
                    "provider": "gemini",
                    "is_configured": False,
                    "base_url": None,
                    "organization": None,
                    "updated_at": None,
                },
            ]
        }
    )


class LLMCredentialsListResponse(BaseModel):
    """List of credential statuses, one entry per supported provider."""

    items: list[LLMCredentialStatus]


# Convenience type for the path-param literal (kept loose to match the
# `model_provider` string used elsewhere; service still validates against
# LLMFactory.supported_providers()).
SupportedProvider = Literal["openai", "gemini", "groq"]
