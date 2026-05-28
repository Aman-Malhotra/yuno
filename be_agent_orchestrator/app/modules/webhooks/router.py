from uuid import UUID

from fastapi import APIRouter, Depends, Path, Request, Response, status

from app.api.deps import get_current_user, get_webhook_service
from app.core.openapi import auth_required_responses
from app.modules.users.models import User
from app.modules.webhooks.schemas import (
    CreateWebhookRequest,
    CreateWebhookResponse,
    WebhookSummary,
)
from app.modules.webhooks.service import WebhookService

router = APIRouter(
    prefix="/workspaces/{workspace_id}/workflows/{workflow_id}/webhooks",
    tags=["workflows"],
)


@router.get(
    "/",
    response_model=list[WebhookSummary],
    status_code=status.HTTP_200_OK,
    summary="List webhooks on a workflow",
    description=(
        "Returns metadata for every webhook on this workflow. The plaintext "
        "token is **never** returned — only the prefix used for UI hinting. "
        "Use this endpoint to display the integration list and rotate keys."
    ),
    operation_id="webhooks_get_list_for_workflow",
    responses=auth_required_responses(404),
)
async def list_webhooks(
    workspace_id: UUID = Path(description="Workspace UUID."),
    workflow_id: UUID = Path(description="Workflow UUID."),
    current_user: User = Depends(get_current_user),
    service: WebhookService = Depends(get_webhook_service),
) -> list[WebhookSummary]:
    rows = await service.list_for_workflow(workspace_id, workflow_id, current_user.id)
    return [WebhookSummary.model_validate(w) for w in rows]


@router.post(
    "/",
    response_model=CreateWebhookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Mint a new webhook token",
    description=(
        "Generates a fresh signing token for this workflow and returns the "
        "plaintext value **exactly once**. Subsequent reads only see the "
        "prefix. Treat the response like an API key — copy it into your "
        "integration immediately. If you lose it, mint a new one and revoke "
        "the old."
    ),
    operation_id="webhooks_post_create",
    responses=auth_required_responses(404, 422),
)
async def create_webhook(
    payload: CreateWebhookRequest,
    request: Request,
    workspace_id: UUID = Path(description="Workspace UUID."),
    workflow_id: UUID = Path(description="Workflow UUID."),
    current_user: User = Depends(get_current_user),
    service: WebhookService = Depends(get_webhook_service),
) -> CreateWebhookResponse:
    webhook, token = await service.create_for_workflow(
        workspace_id, workflow_id, current_user.id, payload
    )
    # Build a copy-pasteable URL relative to the incoming origin so the UI
    # doesn't have to know server-side env.
    base = str(request.base_url).rstrip("/")
    url = f"{base}/api/v1/hooks/{workflow_id}/{token}"
    return CreateWebhookResponse(
        id=webhook.id,
        workspace_id=webhook.workspace_id,
        workflow_id=webhook.workflow_id,
        name=webhook.name,
        status=webhook.status,
        token_prefix=webhook.token_prefix,
        last_used_at=webhook.last_used_at,
        last_used_ip=webhook.last_used_ip,
        last_error=webhook.last_error,
        created_by=webhook.created_by,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at,
        token=token,
        url=url,
    )


@router.delete(
    "/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a webhook token",
    description=(
        "Marks the token revoked. Subsequent calls to the ingress URL with "
        "this token return 404. Revocation is idempotent — calling on an "
        "already-revoked webhook is a no-op."
    ),
    operation_id="webhooks_delete_revoke",
    responses=auth_required_responses(404),
)
async def revoke_webhook(
    workspace_id: UUID = Path(description="Workspace UUID."),
    workflow_id: UUID = Path(description="Workflow UUID."),
    webhook_id: UUID = Path(description="Webhook UUID."),
    current_user: User = Depends(get_current_user),
    service: WebhookService = Depends(get_webhook_service),
) -> Response:
    await service.revoke_for_workflow(workspace_id, workflow_id, webhook_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
