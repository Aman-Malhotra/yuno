"""LLM provider credential vault — per-user.

Endpoints:
- ``GET    /api/v1/llm-providers/``                       — list status per provider
- ``POST   /api/v1/llm-providers/{provider}/credentials`` — set (upsert) creds
- ``GET    /api/v1/llm-providers/{provider}/credentials`` — status for one provider
- ``DELETE /api/v1/llm-providers/{provider}/credentials`` — remove creds

The actual ``api_key`` is never returned by any endpoint; only an
``is_configured: bool`` flag + the non-secret metadata (`base_url`,
`organization`, `updated_at`).
"""

from fastapi import APIRouter, Depends, Path, status

from app.api.deps import get_current_user, get_llm_credentials_service
from app.core.openapi import auth_required_responses
from app.modules.llm.credentials_schemas import (
    LLMCredentialsListResponse,
    LLMCredentialStatus,
    SetLLMCredentialsRequest,
)
from app.modules.llm.credentials_service import LLMCredentialsService
from app.modules.users.models import User

router = APIRouter(prefix="/llm-providers", tags=["llm-providers"])


@router.get(
    "/",
    response_model=LLMCredentialsListResponse,
    status_code=status.HTTP_200_OK,
    summary="List my LLM provider credential statuses",
    description=(
        "Returns one entry per supported provider (`openai`, `gemini`, `groq`), "
        "indicating whether the current user has saved credentials. The actual "
        "API keys are never returned."
    ),
    operation_id="llm_providers_get_list",
    responses=auth_required_responses(),
)
async def list_llm_credentials(
    current_user: User = Depends(get_current_user),
    service: LLMCredentialsService = Depends(get_llm_credentials_service),
) -> LLMCredentialsListResponse:
    items = await service.list_for_user(current_user.id)
    return LLMCredentialsListResponse(items=items)


@router.get(
    "/{provider}/credentials",
    response_model=LLMCredentialStatus,
    status_code=status.HTTP_200_OK,
    summary="Get credential status for one provider",
    description=(
        "Returns the configured-status + non-secret metadata for one provider. "
        "If unconfigured, `is_configured` is `false` and other fields are null."
    ),
    operation_id="llm_providers_get_credentials_status",
    responses=auth_required_responses(422),
)
async def get_llm_credentials_status(
    provider: str = Path(description="Provider key. One of `openai`, `gemini`, `groq`."),
    current_user: User = Depends(get_current_user),
    service: LLMCredentialsService = Depends(get_llm_credentials_service),
) -> LLMCredentialStatus:
    return await service.get_status(current_user.id, provider)


@router.post(
    "/{provider}/credentials",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Set / update LLM provider credentials",
    description=(
        "Upsert credentials for one LLM provider. Returns 204 with no body — the "
        "frontend's `llmProviderApi.registerCredential` parses with `z.void()`. "
        "Refetch via `GET /llm-providers/{provider}/credentials` if you need the "
        "updated status. The submitted payload fully replaces existing credentials "
        "(no deep merge); the actual key is stored in Postgres JSONB, never echoed "
        "back, and redacted in HTTP access logs."
    ),
    operation_id="llm_providers_post_credentials",
    responses=auth_required_responses(422),
)
async def set_llm_credentials(
    payload: SetLLMCredentialsRequest,
    provider: str = Path(description="Provider key."),
    current_user: User = Depends(get_current_user),
    service: LLMCredentialsService = Depends(get_llm_credentials_service),
) -> None:
    await service.set(current_user.id, provider, payload)


@router.delete(
    "/{provider}/credentials",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove LLM provider credentials",
    description=(
        "Deletes the user's stored credentials for one provider. Idempotent — "
        "deleting non-existent credentials returns 204."
    ),
    operation_id="llm_providers_delete_credentials",
    responses=auth_required_responses(422),
)
async def delete_llm_credentials(
    provider: str = Path(description="Provider key."),
    current_user: User = Depends(get_current_user),
    service: LLMCredentialsService = Depends(get_llm_credentials_service),
) -> None:
    await service.delete(current_user.id, provider)
