from uuid import UUID

import structlog

from app.core.config import settings
from app.core.errors import ValidationError
from app.modules.llm.credentials_repository import UserLLMCredentialRepository
from app.modules.llm.credentials_schemas import (
    LLMCredentialStatus,
    SetLLMCredentialsRequest,
)
from app.modules.llm.factory import LLMFactory

log = structlog.get_logger("llm.credentials")


# Map provider key → setting name with the server-level fallback key.
_GLOBAL_KEY_GETTERS: dict[str, str] = {
    "openai": "openai_api_key",
    "gemini": "gemini_api_key",
    "groq": "groq_api_key",
}


def _global_key_for(provider: str) -> str | None:
    attr = _GLOBAL_KEY_GETTERS.get(provider)
    return getattr(settings, attr, None) if attr else None


class LLMCredentialsService:
    def __init__(self, repository: UserLLMCredentialRepository) -> None:
        self.repository = repository

    def _assert_supported(self, provider: str) -> None:
        supported = LLMFactory.supported_providers()
        if provider not in supported:
            raise ValidationError(
                "unsupported_llm_provider",
                f"Unsupported LLM provider {provider!r}.",
                {"supported": supported},
            )

    async def set(
        self,
        user_id: UUID,
        provider: str,
        payload: SetLLMCredentialsRequest,
    ) -> LLMCredentialStatus:
        self._assert_supported(provider)
        row = await self.repository.upsert(
            user_id=user_id,
            provider=provider,
            credentials=payload.model_dump(exclude_none=True),
        )
        log.info(
            "llm.credentials.set",
            user_id=str(user_id),
            provider=provider,
            has_base_url=payload.base_url is not None,
            has_organization=payload.organization is not None,
        )
        return _row_to_status(provider, row)

    async def get_status(self, user_id: UUID, provider: str) -> LLMCredentialStatus:
        self._assert_supported(provider)
        row = await self.repository.get(user_id, provider)
        return _row_to_status(provider, row)

    async def delete(self, user_id: UUID, provider: str) -> None:
        self._assert_supported(provider)
        await self.repository.delete(user_id, provider)
        log.info("llm.credentials.deleted", user_id=str(user_id), provider=provider)

    async def list_for_user(self, user_id: UUID) -> list[LLMCredentialStatus]:
        """Return one status entry per supported provider.

        Builds entries for every supported provider (configured or not),
        so the FE can render the full settings page in one call.
        """

        rows_by_provider = {
            row.provider: row for row in await self.repository.list_for_user(user_id)
        }
        return [
            _row_to_status(provider, rows_by_provider.get(provider))
            for provider in sorted(LLMFactory.supported_providers())
        ]

    # ──────────────────────────────────────────────────────────────────
    # Runtime helpers — used by AgentService.resolve_api_key
    # ──────────────────────────────────────────────────────────────────

    async def has_user_key(self, user_id: UUID, provider: str) -> bool:
        row = await self.repository.get(user_id, provider)
        return bool(row and (row.credentials or {}).get("api_key"))

    async def resolve_api_key(self, user_id: UUID, provider: str) -> str | None:
        """User vault → global env fallback (per-agent BYOK is checked separately by AgentService)."""

        row = await self.repository.get(user_id, provider)
        if row and (api_key := (row.credentials or {}).get("api_key")):
            return api_key  # type: ignore[no-any-return]
        return _global_key_for(provider)


def _row_to_status(provider: str, row: object) -> LLMCredentialStatus:
    if row is None:
        return LLMCredentialStatus(
            provider=provider,
            is_configured=False,
        )
    creds: dict[str, str] = row.credentials or {}  # type: ignore[attr-defined]
    return LLMCredentialStatus(
        provider=provider,
        is_configured=bool(creds.get("api_key")),
        base_url=creds.get("base_url"),
        organization=creds.get("organization"),
        updated_at=row.updated_at,  # type: ignore[attr-defined]
    )
