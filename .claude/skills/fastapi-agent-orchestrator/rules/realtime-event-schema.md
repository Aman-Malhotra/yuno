---
title: One `RuntimeEvent` Schema — Disk, Wire, UI
impact: HIGH
impactDescription: Same shape end-to-end means React can `JSON.parse` and reuse Zod schemas without conversion
tags: realtime, schemas, contract
---

## One `RuntimeEvent` Schema — Disk, Wire, UI

There is **one** Pydantic model for runtime events. It is:

- The row shape in `runtime_events` (after `JSONB` payload merging)
- The bytes sent over Redis pub/sub
- The bytes sent over the WebSocket
- The bytes returned from `GET /runs/{run_id}/events`

The React app parses it once, with a Zod schema that mirrors this model.

### The model

```python
# app/modules/runtime/schemas.py
from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel


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
    id: str | None = None        # set when persisted
    run_id: str
    event_type: RuntimeEventType
    node_id: str | None = None
    agent_id: str | None = None
    message: str | None = None
    payload: dict = {}
    created_at: datetime
```

### Per-event-type `payload` conventions

The `payload` field is JSONB so it's freeform — but agree on shapes per event type so the UI can render consistently.

| event_type           | payload keys                                                                 |
|----------------------|------------------------------------------------------------------------------|
| `run.started`        | `workflow_id`, `input`                                                       |
| `node.started`       | `node_type`                                                                  |
| `agent.thinking`     | (empty)                                                                      |
| `llm.request`        | `model`, `messages` (count, not contents)                                    |
| `llm.response`       | `input_tokens`, `output_tokens`, `cost_usd` (optional)                       |
| `tool.started`       | `tool`, `input`                                                              |
| `tool.completed`     | `tool`, `output`, `duration_ms`                                              |
| `message.sent`       | `from_agent_id`, `to_agent_id`, `channel_type`, `excerpt`                    |
| `node.completed`     | aggregated `input_tokens` + `output_tokens` for the node                     |
| `run.completed`      | `total_input_tokens`, `total_output_tokens`, `total_cost_usd`, `output`      |
| `run.failed`         | `error_code`, `error_message`                                                |

### Don't dump full LLM messages into payload

Storing the whole prompt + response in every event blows up `runtime_events`. Keep `payload` small; if you need the full conversation, query `agent_messages` for that run.

### Bad — multiple shapes for "the same thing"

```python
# ❌ UI has to special-case every emitter
{"event": "llm-response", "tokens_in": 100, "tokens_out": 50}
{"type": "llm_complete", "input_tokens": 100, "output_tokens": 50}
{"kind": "llm.done", "in": 100, "out": 50}
```

### Bad — versioned shapes without a version field

If you ever evolve the schema, add a `schema_version: int = 1` field and rev it. Don't silently change shapes.

### Mirror in the frontend

```ts
// React side — see react-agent-orchestrator skill
const RuntimeEventSchema = z.object({
  id: z.string().nullable(),
  run_id: z.string(),
  event_type: z.nativeEnum(RuntimeEventType),
  node_id: z.string().nullable(),
  agent_id: z.string().nullable(),
  message: z.string().nullable(),
  payload: z.record(z.unknown()),
  created_at: z.string().datetime(),
});
```

### Rules

- One Pydantic model, one enum, one set of payload conventions
- Wire format == DB row shape (serialize/deserialize with `model_dump_json` / `model_validate_json`)
- Token + cost data lives in `payload` so the UI can aggregate live
- `message` is a human-readable short string; `payload` is structured data
- Don't dump full LLM prompts into `payload` — that's what `agent_messages` is for

See: [[runtime-event-emission]], [[realtime-websocket-redis-pubsub]]
