---
title: Channel Webhook + Provider Abstraction
impact: HIGH
impactDescription: The spec requires an external channel (Telegram/Slack/WhatsApp) that a human can chat with — a clean abstraction makes adding the second channel a few-hour job
tags: channels, telegram, slack, webhooks
---

## Channel Webhook + Provider Abstraction

Channels follow the same shape:

```txt
provider:  outbound — send_message(chat_id, text), edit_message, get_me, etc.
webhook:   inbound  — receive, validate signature, persist, enqueue
```

For this assignment, **Telegram** is the required first channel. Slack/WhatsApp follow the same interface.

### Provider base class

```python
# app/modules/channels/providers/base.py
from abc import ABC, abstractmethod
from typing import Any


class ChannelProvider(ABC):
    name: str

    @abstractmethod
    async def send_message(self, chat_id: str, text: str, **opts: Any) -> dict:
        ...

    @abstractmethod
    async def verify_webhook(self, request_body: bytes, headers: dict[str, str]) -> bool:
        ...

    @abstractmethod
    def parse_incoming(self, payload: dict) -> "IncomingMessage":
        ...
```

```python
# app/modules/channels/schemas.py
from pydantic import BaseModel


class IncomingMessage(BaseModel):
    channel_type: str
    external_user_id: str
    external_chat_id: str
    text: str
    raw: dict
```

### Telegram provider

```python
# app/modules/channels/providers/telegram.py
import httpx

from .base import ChannelProvider
from ..schemas import IncomingMessage


class TelegramProvider(ChannelProvider):
    name = "telegram"

    def __init__(self, bot_token: str):
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    async def send_message(self, chat_id: str, text: str, **opts) -> dict:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                f"{self.base_url}/sendMessage",
                json={"chat_id": chat_id, "text": text, **opts},
            )
            r.raise_for_status()
            return r.json()

    async def verify_webhook(self, request_body: bytes, headers: dict[str, str]) -> bool:
        # Telegram doesn't sign payloads; restrict by secret_token header instead.
        return headers.get("x-telegram-bot-api-secret-token") == self.expected_secret

    def parse_incoming(self, payload: dict) -> IncomingMessage:
        msg = payload["message"]
        return IncomingMessage(
            channel_type="telegram",
            external_user_id=str(msg["from"]["id"]),
            external_chat_id=str(msg["chat"]["id"]),
            text=msg.get("text", ""),
            raw=payload,
        )
```

### Registry

```python
# app/modules/channels/registry.py
from app.core.config import settings

from .providers.base import ChannelProvider
from .providers.telegram import TelegramProvider


def build_channel_registry() -> dict[str, ChannelProvider]:
    registry: dict[str, ChannelProvider] = {}
    if settings.telegram_bot_token:
        registry["telegram"] = TelegramProvider(settings.telegram_bot_token)
    return registry
```

### Webhook handler — thin, validates, enqueues

```python
# app/modules/channels/webhooks/telegram.py
from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.deps import get_arq_pool, get_channel_service

router = APIRouter(prefix="/channels/telegram", tags=["channels"])


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    channel_service = Depends(get_channel_service),
    arq_pool = Depends(get_arq_pool),
):
    body = await request.body()
    headers = dict(request.headers)

    provider = channel_service.provider("telegram")
    if not await provider.verify_webhook(body, headers):
        raise HTTPException(status_code=403)

    payload = await request.json()
    incoming = provider.parse_incoming(payload)
    record = await channel_service.record_incoming(incoming)

    await arq_pool.enqueue_job("process_channel_message_job", record.id)
    return {"ok": True}
```

### Worker job — runs the agent

```python
# app/worker/jobs.py
async def process_channel_message_job(ctx, message_id: str) -> None:
    async with AsyncSessionLocal() as db:
        channel_service = ChannelService(...)
        run_service = RunService(...)

        msg = await channel_service.get_message(message_id)
        agent = await channel_service.agent_for_channel(msg.channel_type, msg.external_chat_id)
        if agent is None:
            return  # no agent bound — drop or reply with a default

        run = await run_service.create_run_for_channel(agent.id, msg)
        await run_service.execute(run.id)


async def send_channel_message_job(ctx, channel_type: str, chat_id: str, text: str) -> None:
    provider = ctx["channels"][channel_type]
    await provider.send_message(chat_id, text)
```

### Outbound sends also go through the queue (usually)

The agent executor wants to *reply* — that's another enqueue, so the runtime stays decoupled from HTTP latency to Telegram/Slack:

```python
await arq_pool.enqueue_job("send_channel_message_job", "telegram", chat_id, response_text)
```

### Bad — calling the LLM inside the webhook handler

```python
# ❌ Telegram has a strict webhook ack timeout (~60s); LLMs are slow
@router.post("/webhook")
async def webhook(payload: dict):
    text = await llm.complete(...)              # might take 30s
    await telegram.send_message(chat_id, text)  # another HTTP round-trip
    return {"ok": True}
```

### Bad — `if channel_type == "telegram":` everywhere

```python
# ❌ Adding Slack means touching 12 files
if channel_type == "telegram":
    requests.post("https://api.telegram.org/...", ...)
elif channel_type == "slack":
    requests.post("https://slack.com/api/...", ...)
```

Use the registry + ABC.

### Adding a new channel (instructions for the README)

1. Add a provider class implementing `ChannelProvider` under `providers/`
2. Add a webhook router under `webhooks/`
3. Register the provider in `build_channel_registry()` (gated by an env var)
4. Add the webhook router in `app/api/v1/router.py`

### Rules

- One `ChannelProvider` ABC; one impl per channel
- Webhook: verify → parse → persist → enqueue → return 200 fast
- Outbound sends enqueued, executed by the worker
- Agent ↔ channel binding lives on the agent's `channel_config`
- Telegram first; add Slack/WhatsApp via the same interface

See: [[worker-job-boundary]], [[runtime-event-emission]], [[ops-settings-pydantic]]
