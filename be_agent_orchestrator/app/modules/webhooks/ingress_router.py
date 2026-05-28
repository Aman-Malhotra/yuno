"""Public webhook ingress.

Untrusted callers POST here with a token in the URL. We accept any JSON
object as the run's initial state. No bearer auth — the token is the auth
factor.
"""

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Path, Request, status

from app.api.deps import get_run_service, get_webhook_service, get_workflow_repository
from app.core.errors import NotFoundError
from app.modules.runs.schemas import RunAcknowledgement
from app.modules.runs.service import RunService
from app.modules.webhooks.service import WebhookService
from app.modules.workflows.repository import WorkflowRepository

log = structlog.get_logger("webhooks.ingress")

router = APIRouter(prefix="/hooks", tags=["workflows"])

MAX_BODY_BYTES = 256 * 1024  # 256 KiB — webhook payloads should be small


def _client_ip(request: Request) -> str | None:
    # Trust Forwarded-For only when middleware has populated it; otherwise
    # fall back to the direct peer. (Production reverse proxies should set
    # `X-Forwarded-For` and we'd parse it in middleware, not here.)
    return request.client.host if request.client else None


@router.post(
    "/{workflow_id}/{token}",
    response_model=RunAcknowledgement,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger a workflow via webhook",
    description=(
        "Public ingress endpoint for external integrations. POST a JSON "
        "object — it becomes the run's initial state. The endpoint returns "
        "**202 Accepted** with the new run id; execution happens "
        "asynchronously on the worker.\n\n"
        "No bearer auth: the token in the URL is the only auth factor. "
        "Treat it as a secret.\n\n"
        "Returns 404 (not 401/403) for any auth failure to avoid leaking "
        "which workflows exist."
    ),
    operation_id="webhooks_post_ingest",
    responses={
        404: {"description": "Webhook not found, revoked, or token mismatch"},
        413: {"description": "Body exceeds 256 KiB"},
        422: {"description": "Body is not a JSON object"},
    },
)
async def ingest_webhook(
    request: Request,
    workflow_id: UUID = Path(description="Workflow UUID."),
    token: str = Path(description="Webhook token (begins with `wfh_`)."),
    webhook_service: WebhookService = Depends(get_webhook_service),
    run_service: RunService = Depends(get_run_service),
    workflow_repository: WorkflowRepository = Depends(get_workflow_repository),
) -> RunAcknowledgement:
    # 1. Verify the token first — cheap reject path before parsing the body.
    webhook = await webhook_service.verify(workflow_id, token)
    if webhook is None:
        # Uniform 404. No "invalid token" vs "no such workflow" distinction.
        raise NotFoundError("webhook_not_found", "Webhook not found.", {})

    # 2. Read + parse the body. Body is optional — empty body means "start
    #    with empty state", which is the common case for "ping me to run".
    raw = await request.body()
    if len(raw) > MAX_BODY_BYTES:
        await webhook_service.mark_used(webhook, ip=_client_ip(request), error="body_too_large")
        # 413 surfaces as ValidationError envelope via the generic handler.
        from fastapi import HTTPException

        raise HTTPException(status_code=413, detail="Body too large.")

    input_state: dict[str, Any] = {}
    if raw:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            await webhook_service.mark_used(webhook, ip=_client_ip(request), error="invalid_json")
            from fastapi import HTTPException

            raise HTTPException(status_code=422, detail="Body must be valid JSON.") from None
        if not isinstance(parsed, dict):
            await webhook_service.mark_used(
                webhook, ip=_client_ip(request), error="non_object_body"
            )
            from fastapi import HTTPException

            raise HTTPException(
                status_code=422, detail="Body must be a JSON object (got array/scalar)."
            )
        input_state = parsed

    # 3. Look up the workflow row. We already passed token verification
    #    against this workflow id, so a missing/deleted row is a 404 too.
    workflow = await workflow_repository.get_in_workspace(webhook.workspace_id, workflow_id)
    if workflow is None:
        await webhook_service.mark_used(webhook, ip=_client_ip(request), error="workflow_missing")
        raise NotFoundError("workflow_not_found", "Workflow not found.", {})

    # 4. Queue the run.
    run = await run_service.create_from_webhook(
        workflow=workflow,
        input_state=input_state,
        trigger_source=str(webhook.id),
    )
    await webhook_service.mark_used(webhook, ip=_client_ip(request))

    log.info(
        "webhook.ingest",
        workflow_id=str(workflow_id),
        webhook_id=str(webhook.id),
        run_id=str(run.id),
        ip=_client_ip(request),
        body_bytes=len(raw),
    )

    return RunAcknowledgement(
        run_id=run.id,
        status=run.status,
        accepted_at=datetime.now(UTC),
        input=input_state,
    )
