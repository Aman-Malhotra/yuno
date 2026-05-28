---
title: Every Node Emits Typed Events — Persist + Publish in One Path
impact: CRITICAL
impactDescription: Live monitoring is a grading dimension; events must be reliable, queryable later, AND streamed in real time
tags: runtime, events, observability
---

## Every Node Emits Typed Events — Persist + Publish in One Path

A single `EventEmitter` interface is passed into every node. It does two things atomically:

1. **Persists** the event row to `runtime_events`
2. **Publishes** it to the Redis channel `run:{run_id}`

### The emitter

```python
# app/modules/runtime/events.py
from typing import Any
import json
from datetime import datetime, timezone

from redis.asyncio import Redis

from app.modules.runs.repository import RunEventRepository
from .schemas import RuntimeEvent, RuntimeEventType


class EventEmitter:
    def __init__(self, run_id: str, events: RunEventRepository, redis: Redis):
        self.run_id = run_id
        self.events = events
        self.redis = redis

    async def emit(
        self,
        event_type: RuntimeEventType,
        node_id: str | None = None,
        agent_id: str | None = None,
        message: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        event = RuntimeEvent(
            run_id=self.run_id,
            event_type=event_type,
            node_id=node_id,
            agent_id=agent_id,
            message=message,
            payload=payload or {},
            created_at=datetime.now(timezone.utc),
        )

        # Persist first — if we crash before publishing, the UI can replay from DB
        await self.events.insert(event)

        # Then publish for live subscribers
        await self.redis.publish(
            f"run:{self.run_id}",
            event.model_dump_json(),
        )
```

### Event type enum

```python
# app/modules/runtime/schemas.py
from enum import StrEnum
from pydantic import BaseModel
from datetime import datetime


class RuntimeEventType(StrEnum):
    RUN_STARTED = "run.started"
    NODE_STARTED = "node.started"
    AGENT_THINKING = "agent.thinking"
    LLM_REQUEST = "llm.request"
    LLM_RESPONSE = "llm.response"
    TOOL_STARTED = "tool.started"
    TOOL_COMPLETED = "tool.completed"
    MESSAGE_SENT = "message.sent"
    NODE_COMPLETED = "node.completed"
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"


class RuntimeEvent(BaseModel):
    run_id: str
    event_type: RuntimeEventType
    node_id: str | None = None
    agent_id: str | None = None
    message: str | None = None
    payload: dict = {}
    created_at: datetime
```

### Used by a node

```python
# app/modules/runtime/agent_executor.py
def build_agent_node(node_id, agent_id, load_agent, emit: EventEmitter):
    async def node(state: RuntimeState) -> RuntimeState:
        agent = await load_agent(agent_id)

        await emit.emit(
            RuntimeEventType.NODE_STARTED,
            node_id=node_id,
            agent_id=agent_id,
            message=f"entering {agent.name}",
        )
        await emit.emit(RuntimeEventType.AGENT_THINKING, node_id=node_id, agent_id=agent_id)

        response, usage = await run_agent_turn(agent, state, emit)

        await emit.emit(
            RuntimeEventType.NODE_COMPLETED,
            node_id=node_id,
            agent_id=agent_id,
            payload={
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
            },
        )
        state.messages.append(response)
        return state
    return node
```

### Order matters — persist before publish

If we publish first and crash before the DB insert, a WS client may see an event that doesn't exist on reconnect. Persist first guarantees the DB is the source of truth.

### Bad — emitting only to Redis

```python
# ❌ Refresh the UI → events gone
await redis.publish(f"run:{run_id}", json.dumps(event))
```

The UI needs `GET /runs/{run_id}/events` to backfill on connect. That only works if events are in the DB.

### Bad — emitting only to the DB

```python
# ❌ Live monitoring stops working
await events_repo.insert(event)
```

### Bad — bespoke event payload shapes per node

```python
# ❌ UI can't switch on event_type
await emit("agent_thinking_event", {"the_agent": agent_id})
await emit("LLM_REQ", {"agent": agent_id})
```

### Rules

- One `RuntimeEvent` Pydantic model. Wire shape == disk shape.
- One enum `RuntimeEventType`. Adding an event type = adding an enum member + emitting it.
- Always persist before publish.
- WS handler backfills from DB on connect, then subscribes for new events. See [[realtime-websocket-redis-pubsub]].
- LLM/tool token + cost data goes in `payload` so the UI can sum it live.

See: [[runtime-workflow-compiler]], [[runtime-agent-executor]], [[realtime-websocket-redis-pubsub]], [[realtime-event-schema]]
