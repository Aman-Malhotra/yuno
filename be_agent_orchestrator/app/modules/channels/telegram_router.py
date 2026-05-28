"""Telegram Bot API → workflow run ingress.

Single public endpoint that the Telegram platform calls when our bot
receives a message. We translate the Bot API ``Update`` envelope into a
workflow run with state = ``{message, chat_id, user, ...}``, enqueue
``execute_workflow_run_job``, and return 200 — Telegram retries on any
non-2xx for ~24h, which is the wrong recovery model for us.

Auth model
----------
Telegram supports an optional ``X-Telegram-Bot-Api-Secret-Token`` header
set when calling ``setWebhook``. We require that header to match
``settings.telegram_webhook_secret`` on every request — without it, anyone
who knows the public URL could fire workflows. The secret is opaque to the
bot owner (we generate it once at setup) so leaking the URL alone is not
enough.

Routing
-------
For v1 a single workflow handles all inbound Telegram messages — the id is
configured via ``TELEGRAM_WORKFLOW_ID`` in env. Multi-workspace / per-chat
binding is a later concern; the current product surface is one demo bot
per deploy.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.api.deps import get_run_service, get_workflow_repository
from app.core.config import settings
from app.modules.runs.service import RunService
from app.modules.workflows.repository import WorkflowRepository

log = structlog.get_logger("channels.telegram")

router = APIRouter(prefix="/channels/telegram", tags=["channels"])


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Telegram Bot API webhook receiver",
    description=(
        "Public endpoint registered with Telegram via `setWebhook`. Each "
        "inbound user message becomes a workflow run.\n\n"
        "Auth: the request must carry `X-Telegram-Bot-Api-Secret-Token` "
        "matching the server's `TELEGRAM_WEBHOOK_SECRET` (set the same value "
        "when calling `setWebhook`).\n\n"
        "Behavior: always returns 200 unless authentication fails (401). "
        "Internal errors are logged but **not** surfaced to Telegram so the "
        "platform doesn't retry-storm us on a transient backend hiccup."
    ),
    operation_id="channels_telegram_webhook",
    responses={
        401: {"description": "Missing or wrong secret token"},
        503: {"description": "Telegram workflow id not configured on server"},
    },
)
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
    run_service: RunService = Depends(get_run_service),
    workflow_repository: WorkflowRepository = Depends(get_workflow_repository),
) -> dict[str, Any]:
    # 1. Auth — constant header check. Refuse if either side is unset so
    #    you can't accidentally open the bot by forgetting the env var.
    expected = settings.telegram_webhook_secret
    if not expected:
        raise HTTPException(status_code=401, detail="telegram secret not configured on server")
    if x_telegram_bot_api_secret_token != expected:
        raise HTTPException(status_code=401, detail="bad telegram secret token")

    # 2. Resolve the target workflow from env. 503 (not 500) so Telegram's
    #    retry queue clears it as "service unavailable" rather than burning
    #    cycles on a misconfigured deploy.
    if not settings.telegram_workflow_id or not settings.telegram_workspace_id:
        log.warning("telegram.webhook.unconfigured")
        raise HTTPException(status_code=503, detail="telegram workflow not configured")

    try:
        workflow_id = UUID(settings.telegram_workflow_id)
        workspace_id = UUID(settings.telegram_workspace_id)
    except ValueError as err:
        raise HTTPException(status_code=503, detail=f"bad telegram config: {err}") from err

    # 3. Parse the Bot API update envelope. Telegram sends a wide schema;
    #    we only care about ``message`` and ``edited_message`` text updates
    #    for v1. Other update types (callback queries, inline queries) just
    #    ack with 200 so the platform doesn't retry.
    update = await request.json()
    extracted = _extract_message(update)
    if extracted is None:
        log.info("telegram.webhook.unsupported_update", keys=list(update.keys()))
        return {"ok": True, "ignored": True}

    workflow = await workflow_repository.get_in_workspace(workspace_id, workflow_id)
    if workflow is None:
        log.warning(
            "telegram.webhook.workflow_missing",
            workflow_id=str(workflow_id),
            workspace_id=str(workspace_id),
        )
        return {"ok": True, "error": "workflow_missing"}

    # Flatten the keys the runtime + memory hooks read so they don't have
    # to dig into ``user`` or ``telegram_update``. ``telegram_user_id`` is
    # the stable numeric id (mem0 partition key); ``username`` is the
    # display handle (attached as memory metadata, queryable in the UI).
    initial_state = {
        "channel": "telegram",
        "message": extracted["text"],
        "chat_id": extracted["chat_id"],
        "telegram_user_id": extracted["user"]["id"],
        "username": extracted["user"].get("username"),
        "user": extracted["user"],
        "telegram_update": update,
    }
    run = await run_service.create_from_webhook(
        workflow=workflow,
        input_state=initial_state,
        trigger_source=f"telegram:{extracted['chat_id']}",
    )
    log.info(
        "telegram.webhook.queued",
        run_id=str(run.id),
        chat_id=extracted["chat_id"],
        text_preview=extracted["text"][:80],
    )

    return {"ok": True, "run_id": str(run.id)}


def _extract_message(update: dict[str, Any]) -> dict[str, Any] | None:
    """Pull the user-facing message out of a Bot API Update.

    Returns ``None`` if the update is something we don't handle (edited
    messages, callback queries, channel posts, …).
    """

    msg = update.get("message") or update.get("edited_message")
    if not isinstance(msg, dict):
        return None
    text = msg.get("text")
    if not isinstance(text, str) or not text.strip():
        return None
    chat = msg.get("chat") or {}
    user = msg.get("from") or {}
    return {
        "text": text,
        "chat_id": chat.get("id"),
        "user": {
            "id": user.get("id"),
            "username": user.get("username"),
            "first_name": user.get("first_name"),
            "last_name": user.get("last_name"),
        },
    }
