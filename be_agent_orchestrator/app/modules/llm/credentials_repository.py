from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.llm.models import UserLLMCredential


class UserLLMCredentialRepository:
    """All DB access for ``user_llm_credentials``."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, user_id: UUID, provider: str) -> UserLLMCredential | None:
        stmt = select(UserLLMCredential).where(
            UserLLMCredential.user_id == user_id,
            UserLLMCredential.provider == provider,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_for_user(self, user_id: UUID) -> list[UserLLMCredential]:
        stmt = (
            select(UserLLMCredential)
            .where(UserLLMCredential.user_id == user_id)
            .order_by(UserLLMCredential.provider)
        )
        return list((await self.db.execute(stmt)).scalars())

    async def upsert(
        self,
        *,
        user_id: UUID,
        provider: str,
        credentials: dict[str, Any],
    ) -> UserLLMCredential:
        """Insert or overwrite the (user, provider) row.

        Full replacement of the ``credentials`` JSONB (not a deep merge) —
        unsetting `base_url` means re-posting without it.
        """

        existing = await self.get(user_id, provider)
        if existing is None:
            row = UserLLMCredential(
                user_id=user_id,
                provider=provider,
                credentials=credentials,
            )
            self.db.add(row)
        else:
            existing.credentials = credentials
            row = existing
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def delete(self, user_id: UUID, provider: str) -> None:
        stmt = delete(UserLLMCredential).where(
            UserLLMCredential.user_id == user_id,
            UserLLMCredential.provider == provider,
        )
        await self.db.execute(stmt)
        await self.db.commit()
