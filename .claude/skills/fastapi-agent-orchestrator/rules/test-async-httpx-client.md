---
title: Tests Use `httpx.AsyncClient` Against the ASGI App
impact: HIGH
impactDescription: In-process ASGI tests are fast and exercise the real router/middleware/deps — no live uvicorn needed
tags: testing, httpx, async
---

## Tests Use `httpx.AsyncClient` Against the ASGI App

No `uvicorn`-in-a-thread, no `requests`, no `TestClient` from FastAPI (which is sync-only).

### Why

- Hits the **real** ASGI pipeline: middleware, exception handlers, dependencies
- Truly async — no thread juggling
- Works with `app.dependency_overrides` for clean stubbing

### Fixture

```python
# tests/conftest.py
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.session import get_db_session
from app.modules.auth.dependencies import get_current_user


@pytest_asyncio.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        # run inside a transaction we roll back at the end
        async with session.begin():
            yield session
            await session.rollback()


@pytest_asyncio.fixture
async def client(db_session, current_user):
    async def _db():
        yield db_session

    async def _user():
        return current_user

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = _user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()
```

### Usage

```python
# tests/test_agent_creation.py
import pytest


@pytest.mark.asyncio
async def test_create_agent(client):
    r = await client.post("/api/v1/agents/", json={
        "name": "Helper",
        "role": "assistant",
        "system_prompt": "Be helpful.",
        "model_provider": "openai",
        "model_name": "gpt-4o-mini",
    })
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Helper"

    r2 = await client.get(f"/api/v1/agents/{body['id']}")
    assert r2.status_code == 200
    assert r2.json()["id"] == body["id"]
```

### pytest-asyncio config

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

So every `async def test_*` is automatically run as async — no `@pytest.mark.asyncio` repeated everywhere.

### Stubbing dependencies

`app.dependency_overrides` is the canonical mechanism. Always clear in the fixture teardown so tests don't leak overrides into each other.

```python
app.dependency_overrides[get_llm_service] = lambda: FakeLLMService(scripted)
app.dependency_overrides[get_channel_service] = lambda: FakeChannelService()
```

### Bad — `TestClient` for async code

```python
# ❌ TestClient runs the app in a thread; doesn't mix with async fixtures
from fastapi.testclient import TestClient
client = TestClient(app)
```

### Bad — booting uvicorn in a subprocess for tests

```python
# ❌ Slow, flaky, port conflicts
proc = subprocess.Popen(["uvicorn", "app.main:app"])
```

### Bad — making real HTTP calls to OpenAI / Telegram

Stub at the dependency level instead — see [[test-critical-paths]].

### Rules

- One `client` fixture; one `db_session` fixture per-test transaction
- `asyncio_mode = "auto"` in pyproject
- All external services (LLM, Telegram) stubbed via `dependency_overrides`
- Tests reset `app.dependency_overrides` at the end of each test
- No `TestClient`, no `requests`, no live uvicorn

See: [[test-critical-paths]], [[api-dependency-injection]]
