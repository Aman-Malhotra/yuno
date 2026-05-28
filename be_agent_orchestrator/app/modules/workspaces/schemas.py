from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

WorkspaceRole = Literal["owner", "admin", "member", "viewer"]


# ──────────────────────────────────────────────────────────────────────
# Requests
# ──────────────────────────────────────────────────────────────────────


class CreateWorkspaceRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=255,
        description="Human-readable workspace name. Slug is derived server-side.",
    )

    model_config = ConfigDict(json_schema_extra={"examples": [{"name": "Acme Engineering"}]})


# ──────────────────────────────────────────────────────────────────────
# Responses
# ──────────────────────────────────────────────────────────────────────


class WorkspaceSummary(BaseModel):
    """Shape returned by the landing-page list endpoint.

    Includes the role the *current* user has in the workspace so the UI
    can render the "owner" / "viewer" badge without a second call.
    """

    id: UUID
    name: str
    slug: str
    role: WorkspaceRole = Field(description="Current user's role in this workspace.")
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "01HZX9F4Y0N0N5J5R0Q6Z3M8B2",
                    "name": "Aman's Workspace",
                    "slug": "aman-workspace",
                    "role": "owner",
                    "created_at": "2026-05-23T18:42:13.812000Z",
                }
            ]
        },
    )
