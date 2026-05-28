"""Workspace-scoped LLM credential service.

Single source of truth for "is this provider available as a default in
this workspace?". Read by:
- The agent-create flow (relax BYOK requirement when workspace covers it)
- The runtime resolver (chain: agent → workspace → fail)
- The agent capabilities endpoint (mark providers ``is_configured`` when
  the workspace has them)
"""

from __future__ import annotations

from uuid import UUID

import structlog

from app.core.errors import NotFoundError, ValidationError
from app.modules.llm.factory import LLMFactory
from app.modules.llm.models import WorkspaceLLMCredential
from app.modules.llm.workspace_credentials_repository import (
    WorkspaceLLMCredentialRepository,
)
from app.modules.llm.workspace_credentials_schemas import (
    CreateWorkspaceCredentialRequest,
    UpdateWorkspaceCredentialRequest,
    WorkspaceCredentialSummary,
)
from app.modules.workspaces.service import WorkspaceService

log = structlog.get_logger("llm.workspace_credentials")


class WorkspaceLLMCredentialService:
    def __init__(
        self,
        repository: WorkspaceLLMCredentialRepository,
        workspace_service: WorkspaceService,
    ) -> None:
        self.repository = repository
        self.workspace_service = workspace_service

    def _assert_supported(self, provider: str) -> None:
        supported = LLMFactory.supported_providers()
        if provider not in supported:
            raise ValidationError(
                "unsupported_llm_provider",
                f"Unsupported LLM provider {provider!r}.",
                {"supported": supported},
            )

    async def list_for_workspace(
        self, workspace_id: UUID, user_id: UUID
    ) -> list[WorkspaceCredentialSummary]:
        await self.workspace_service.get_role_or_403(workspace_id, user_id)
        rows = await self.repository.list_for_workspace(workspace_id)
        return [_row_to_summary(row) for row in rows]

    async def create(
        self,
        workspace_id: UUID,
        user_id: UUID,
        payload: CreateWorkspaceCredentialRequest,
    ) -> WorkspaceCredentialSummary:
        await self.workspace_service.get_role_or_403(workspace_id, user_id)
        self._assert_supported(payload.provider)

        creds: dict[str, str] = {"api_key": payload.api_key}
        if payload.base_url:
            creds["base_url"] = payload.base_url
        if payload.organization:
            creds["organization"] = payload.organization

        row = await self.repository.upsert(
            workspace_id=workspace_id,
            provider=payload.provider,
            credentials=creds,
            created_by=user_id,
        )
        log.info(
            "llm.workspace_credentials.set",
            workspace_id=str(workspace_id),
            provider=payload.provider,
            actor_user_id=str(user_id),
        )
        return _row_to_summary(row)

    async def update(
        self,
        workspace_id: UUID,
        credential_id: UUID,
        user_id: UUID,
        payload: UpdateWorkspaceCredentialRequest,
    ) -> WorkspaceCredentialSummary:
        await self.workspace_service.get_role_or_403(workspace_id, user_id)
        row = await self.repository.get_by_id(workspace_id, credential_id)
        if row is None:
            raise NotFoundError(
                "workspace_credential_not_found",
                "Credential does not exist in this workspace.",
                {"workspace_id": str(workspace_id), "credential_id": str(credential_id)},
            )

        # Build the merged credential dict. Empty string => unset.
        creds = dict(row.credentials or {})
        if payload.api_key is not None:
            creds["api_key"] = payload.api_key
        if payload.base_url is not None:
            if payload.base_url == "":
                creds.pop("base_url", None)
            else:
                creds["base_url"] = payload.base_url
        if payload.organization is not None:
            if payload.organization == "":
                creds.pop("organization", None)
            else:
                creds["organization"] = payload.organization

        row = await self.repository.upsert(
            workspace_id=workspace_id,
            provider=row.provider,
            credentials=creds,
            created_by=row.created_by,
        )
        log.info(
            "llm.workspace_credentials.updated",
            workspace_id=str(workspace_id),
            credential_id=str(credential_id),
            actor_user_id=str(user_id),
        )
        return _row_to_summary(row)

    async def delete(self, workspace_id: UUID, credential_id: UUID, user_id: UUID) -> None:
        await self.workspace_service.get_role_or_403(workspace_id, user_id)
        ok = await self.repository.delete_by_id(workspace_id, credential_id)
        if not ok:
            raise NotFoundError(
                "workspace_credential_not_found",
                "Credential does not exist in this workspace.",
                {"workspace_id": str(workspace_id), "credential_id": str(credential_id)},
            )
        log.info(
            "llm.workspace_credentials.deleted",
            workspace_id=str(workspace_id),
            credential_id=str(credential_id),
            actor_user_id=str(user_id),
        )

    # ──────────────────────────────────────────────────────────────────
    # Runtime helpers — used by AgentService
    # ──────────────────────────────────────────────────────────────────

    async def resolve_api_key(self, workspace_id: UUID, provider: str) -> str | None:
        """Return the workspace's stored api_key for ``provider`` or None."""

        row = await self.repository.get(workspace_id, provider)
        if row is None:
            return None
        return (row.credentials or {}).get("api_key") or None

    async def configured_providers(self, workspace_id: UUID) -> set[str]:
        return await self.repository.configured_providers(workspace_id)


def _row_to_summary(row: WorkspaceLLMCredential) -> WorkspaceCredentialSummary:
    creds = row.credentials or {}
    api_key = str(creds.get("api_key") or "")
    last4 = "…" + api_key[-4:] if len(api_key) >= 4 else "…"
    return WorkspaceCredentialSummary(
        id=row.id,
        workspace_id=row.workspace_id,
        provider=row.provider,
        last4=last4,
        base_url=creds.get("base_url"),
        organization=creds.get("organization"),
        created_by=row.created_by,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
