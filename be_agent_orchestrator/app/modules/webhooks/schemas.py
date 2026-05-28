from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

WebhookStatus = Literal["active", "revoked"]


class CreateWebhookRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=120,
        description="Display name for the webhook — used to identify it in the UI when rotating keys.",
    )

    @field_validator("name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be blank")
        return v

    model_config = ConfigDict(extra="forbid")


class WebhookSummary(BaseModel):
    """List/read shape — never includes the plaintext token."""

    id: UUID
    workspace_id: UUID
    workflow_id: UUID
    name: str
    status: WebhookStatus
    token_prefix: str = Field(
        description="First 8 chars of the plaintext token. Safe to show in UI for disambiguation."
    )
    last_used_at: datetime | None = None
    last_used_ip: str | None = None
    last_error: str | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreateWebhookResponse(WebhookSummary):
    """One-shot create response — includes the plaintext token + URL.

    The plaintext token is **never returned again**. Surface it to the user
    immediately and treat it like an API key on the client side.
    """

    token: str = Field(description="Full plaintext token. Shown once at creation.")
    url: str = Field(description="Full webhook URL ready to paste into an integration.")
