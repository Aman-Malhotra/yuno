"""Request + response shapes for workspace-scoped LLM credentials."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateWorkspaceCredentialRequest(BaseModel):
    """Add a workspace-default credential for a single provider.

    Upsert: one row per (workspace, provider). Re-posting overwrites the
    existing row's credential block (same behavior as the user vault).
    """

    provider: str = Field(
        min_length=1,
        max_length=64,
        description="LLM provider key (`openai` | `gemini` | `groq`).",
    )
    api_key: str = Field(min_length=1, description="Provider API key.")
    base_url: str | None = Field(default=None)
    organization: str | None = Field(default=None)


class UpdateWorkspaceCredentialRequest(BaseModel):
    """Rotate or amend an existing row.

    Every field is optional — omit to leave unchanged. To clear
    ``base_url`` / ``organization``, pass an empty string and the service
    treats it as null.
    """

    api_key: str | None = Field(default=None, min_length=1)
    base_url: str | None = None
    organization: str | None = None

    model_config = ConfigDict(extra="forbid")


class WorkspaceCredentialSummary(BaseModel):
    """The shape we hand to the FE — never carries the raw api_key.

    ``last4`` is the last four characters of the key, used to disambiguate
    multiple rows in the UI without exposing the secret.
    """

    id: UUID
    workspace_id: UUID
    provider: str
    last4: str = Field(description='Last four chars of the api_key, prefixed with "…".')
    base_url: str | None = None
    organization: str | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class WorkspaceCredentialListResponse(BaseModel):
    items: list[WorkspaceCredentialSummary]
