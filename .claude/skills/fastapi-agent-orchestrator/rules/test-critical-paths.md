---
title: Tests for Critical Paths
impact: HIGH
impactDescription: The spec grades tests for agent creation, workflow execution, and message delivery — these are the must-pass cases
tags: testing, pytest, critical-paths
---

## Tests for Critical Paths

The spec calls out three critical paths explicitly. The test suite is small but covers them end-to-end.

### Required tests

```txt
tests/
  conftest.py
  test_auth.py
  test_agent_creation.py
  test_workflow_validation.py
  test_workflow_execution.py
  test_runtime_event_persisted.py
  test_agent_message_delivery.py
  test_telegram_webhook_enqueues.py
```

### What each test asserts

| File                              | What it asserts                                                                                       |
|-----------------------------------|-------------------------------------------------------------------------------------------------------|
| `test_auth.py`                    | register + login returns access+refresh; protected route returns 401 without token, 200 with token    |
| `test_agent_creation.py`          | POST /agents persists + returns; GET /agents/{id} returns the same; cross-user GET returns 403/404    |
| `test_workflow_validation.py`     | invalid graph → 422; valid graph → 200; cycle without condition → 422                                 |
| `test_workflow_execution.py`      | POST /run enqueues; worker runs end-to-end with a stubbed LLM; run.status flips queued → completed    |
| `test_runtime_event_persisted.py` | after a run, `runtime_events` has `run.started` + at least one `node.started` + `run.completed`       |
| `test_agent_message_delivery.py`  | two-agent workflow persists messages in `agent_messages` with `from_agent_id`/`to_agent_id`           |
| `test_telegram_webhook_enqueues.py` | POST /channels/telegram/webhook with valid secret → 200 + arq job enqueued (use a mock pool)         |

### Stubbing the LLM

Don't hit real providers from tests. Inject a fake `LLMProvider` via `app.dependency_overrides`:

```python
# tests/conftest.py
class FakeLLMProvider:
    name = "openai"

    def __init__(self, scripted_responses):
        self.scripted = list(scripted_responses)

    async def complete(self, request):
        return self.scripted.pop(0)

    async def stream(self, request):
        ...
```

```python
# tests/test_workflow_execution.py
async def test_workflow_runs_end_to_end(client, db, override_llm):
    override_llm([
        LLMResponse(message=LLMMessage(role="assistant", content="hello back"), usage=TokenUsage(10, 5)),
    ])

    # create agent + workflow via API
    agent = await create_agent_via_api(client)
    wf = await create_simple_one_node_workflow(client, agent.id)

    # enqueue + execute synchronously in the test
    run = await client.post(f"/api/v1/workflows/{wf.id}/run", json={"input": {"q": "hi"}})
    run_id = run.json()["id"]

    await execute_workflow_job({"redis": fake_redis}, run_id)

    events = await client.get(f"/api/v1/runs/{run_id}/events")
    types = [e["event_type"] for e in events.json()]
    assert "run.started" in types
    assert "run.completed" in types
```

### Stubbing the worker

For request-side tests, override `get_arq_pool` with a fake pool that records `enqueue_job` calls:

```python
class FakeArqPool:
    def __init__(self):
        self.calls: list[tuple[str, tuple]] = []

    async def enqueue_job(self, name, *args, **kwargs):
        self.calls.append((name, args))
```

### Test DB strategy

- **Default:** a real Postgres in `docker-compose.test.yml`; one DB per test session, schema created with `alembic upgrade head`, transactions rolled back per test
- **If time-constrained:** `testcontainers-python` to spin Postgres per session
- Avoid SQLite — JSONB is required and behaves differently

### Async test setup

```python
# tests/conftest.py
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
```

### Rules

- These tests are the **acceptance bar**. Any PR that breaks one of them does not ship.
- Tests use the real ASGI app via `httpx.AsyncClient` — see [[test-async-httpx-client]]
- LLM + Telegram providers are always stubbed in tests
- Worker jobs are invoked **directly** in execution tests (no real Arq queue), so the test runs in-process

See: [[test-async-httpx-client]], [[runtime-event-emission]], [[worker-job-boundary]]
