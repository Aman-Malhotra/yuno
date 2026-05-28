---
title: WebSocket Fan-Out via Redis Pub/Sub
impact: HIGH
impactDescription: The spec requires live logs and inter-agent messages; pub/sub lets the worker emit once and any number of WS clients receive
tags: realtime, websocket, redis, pubsub
---

## WebSocket Fan-Out via Redis Pub/Sub

The worker publishes runtime events to a Redis channel; the API subscribes per WebSocket client. Multiple API replicas can serve the same run because Redis is the bus.

### End-to-end flow

```txt
worker  ── EventEmitter.emit() ──► insert into runtime_events
                                  └► PUBLISH run:{run_id} <JSON event>
                                            │
            ┌───────────────────────────────┘
            ▼
api  ── WS /api/v1/monitoring/runs/{run_id}
        1) fetch backfill from runtime_events
        2) SUBSCRIBE run:{run_id}
        3) forward each message to the client
```

### WebSocket endpoint

```python
# app/modules/monitoring/router.py
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from app.api.deps import get_connection_manager, get_run_service
from app.core.security import decode_access_token
from app.modules.runs.service import RunService

from .connection_manager import ConnectionManager


router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.websocket("/runs/{run_id}")
async def run_events_ws(
    websocket: WebSocket,
    run_id: str,
    token: str = Query(...),
    manager: ConnectionManager = Depends(get_connection_manager),
    run_service: RunService = Depends(get_run_service),
):
    try:
        payload = decode_access_token(token)
        user_id = payload["sub"]
    except Exception:
        await websocket.close(code=4401)
        return

    # permission check + 404 handling lives in the service
    await run_service.get_run(user_id, run_id)

    await websocket.accept()

    # 1) backfill — events that already happened
    backfill = await run_service.list_events(run_id)
    for ev in backfill:
        await websocket.send_text(ev.model_dump_json())

    # 2) subscribe for new events
    try:
        await manager.subscribe(websocket, run_id)
    except WebSocketDisconnect:
        pass
```

### Connection manager

```python
# app/modules/monitoring/connection_manager.py
import asyncio
from fastapi import WebSocket
from redis.asyncio import Redis


class ConnectionManager:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def subscribe(self, websocket: WebSocket, run_id: str) -> None:
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(f"run:{run_id}")
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                await websocket.send_bytes(message["data"])
        finally:
            await pubsub.unsubscribe(f"run:{run_id}")
            await pubsub.aclose()
```

### Why pub/sub instead of in-process dict

- The worker and API are **different processes**. An in-process `dict[run_id, list[websocket]]` in the API can't see events emitted by the worker.
- Redis pub/sub is at-most-once — fine, because clients also have a DB backfill on connect.

### Backfill is non-negotiable

If a client connects mid-run, it must see events 1..N from the DB before subscribing to new ones. Otherwise the UI shows partial history.

### Bad — in-process queue only

```python
# ❌ Only works if worker == API (it isn't)
queues: dict[str, asyncio.Queue] = {}
```

### Bad — polling the DB from the WS

```python
# ❌ Latency + DB load for every WS client
while True:
    new = await events_repo.since(run_id, last_id)
    for ev in new: await ws.send_text(ev.json())
    await asyncio.sleep(0.5)
```

### Bad — emitting only over the WS bus, never persisting

See [[runtime-event-emission]] — persist first.

### Rules

- Channel name: `run:{run_id}` (UUID string)
- Wire format: the `RuntimeEvent` JSON, as bytes
- WS connects with `?token=<jwt>` query param; close with `4401` on bad token
- Always backfill from DB on connect, then subscribe for new
- One `ConnectionManager` per process — built once in `lifespan`, injected via `Depends`

See: [[runtime-event-emission]], [[realtime-event-schema]], [[auth-current-user-dep]]
