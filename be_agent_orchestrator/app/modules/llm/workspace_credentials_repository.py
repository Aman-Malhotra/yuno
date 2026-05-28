"""DB access for ``workspace_llm_credentials``.

Mirrors ``UserLLMCredentialRepository`` (per-user vault) — same shape,
different scope. One row per (workspace, provider); the ``credentials``
JSONB holds ``{api_key, base_url, organization}``.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.llm.models import WorkspaceLLMCredential


class WorkspaceLLMCredentialRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, workspace_id: UUID, provider: str) -> WorkspaceLLMCredential | None:
        stmt = select(WorkspaceLLMCredential).where(
            WorkspaceLLMCredential.workspace_id == workspace_id,
            WorkspaceLLMCredential.provider == provider,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_by_id(
        self, workspace_id: UUID, credential_id: UUID
    ) -> WorkspaceLLMCredential | None:
        stmt = select(WorkspaceLLMCredential).where(
            WorkspaceLLMCredential.workspace_id == workspace_id,
            WorkspaceLLMCredential.id == credential_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_for_workspace(self, workspace_id: UUID) -> list[WorkspaceLLMCredential]:
        stmt = (
            select(WorkspaceLLMCredential)
            .where(WorkspaceLLMCredential.workspace_id == workspace_id)
            .order_by(WorkspaceLLMCredential.provider)
        )
        return list((await self.db.execute(stmt)).scalars())

    async def upsert(
        self,
        *,
        workspace_id: UUID,
        provider: str,
        credentials: dict[str, Any],
        created_by: UUID | None,
    ) -> WorkspaceLLMCredential:
        """Insert-or-overwrite the (workspace, provider) row.

        Full replacement of the credentials dict — unsetting ``base_url``
        means re-posting without it. Mirrors the user-vault behavior so
        the two surfaces feel identical.
        """

        existing = await self.get(workspace_id, provider)
        if existing is None:
            row = WorkspaceLLMCredential(
                workspace_id=workspace_id,
                provider=provider,
                credentials=credentials,
                created_by=created_by,
            )
            self.db.add(row)
        else:
            existing.credentials = credentials
            row = existing
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def delete_by_id(self, workspace_id: UUID, credential_id: UUID) -> bool:
        stmt = delete(WorkspaceLLMCredential).where(
            WorkspaceLLMCredential.workspace_id == workspace_id,
            WorkspaceLLMCredential.id == credential_id,
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return bool(result.rowcount)

    async def configured_providers(self, workspace_id: UUID) -> set[str]:
        """Set of provider keys this workspace has a real api_key for.

        Used by the capabilities endpoint to mark providers as
        pre-configured in the agent-create form.
        """

        rows = await self.list_for_workspace(workspace_id)
        return {r.provider for r in rows if (r.credentials or {}).get("api_key")}
