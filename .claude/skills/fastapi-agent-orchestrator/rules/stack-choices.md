---
title: Stack Choices
impact: CRITICAL
impactDescription: Locks the technology decisions that every other rule assumes; deviating breaks the rest of the architecture
tags: stack, dependencies, fastapi, langgraph
---

## Stack Choices

The Yuno backend uses a **fixed, justified stack**. Do not swap pieces silently — every rule downstream assumes these.

| Concern              | Choice                          | Why                                                                  |
|----------------------|----------------------------------|----------------------------------------------------------------------|
| Web framework        | FastAPI                          | Async, Pydantic-native, WebSocket support, fast to scaffold          |
| Agent runtime        | LangGraph                        | Graph maps 1:1 to the visual workflow builder; supports loops/conditions |
| Database             | PostgreSQL 16                    | JSONB for graph/config blobs; durable persistence                    |
| ORM                  | SQLAlchemy 2.0 async + asyncpg   | First-class async; matches FastAPI's event loop                      |
| Migrations           | Alembic                          | Standard with SQLAlchemy                                             |
| Validation           | Pydantic v2                      | Shared request/response/event/state schemas                          |
| Queue / worker       | Redis + Arq                      | Lightweight, async-native, no Celery boilerplate                     |
| Realtime             | WebSocket + Redis pub/sub        | Bidirectional; survives multiple API replicas                        |
| Auth                 | JWT access + opaque refresh      | Stateless API, revocable refresh                                     |
| Password hashing     | `pwdlib[argon2]`                 | Argon2id is the current best practice                                |
| Settings             | `pydantic-settings` + `.env`     | Single typed config object                                           |
| HTTP client          | `httpx`                          | Async, same API as `requests`                                        |
| Testing              | `pytest` + `pytest-asyncio` + `httpx.AsyncClient` | ASGI in-process tests, no live server needed         |
| Logging              | `structlog`                      | Structured key/value logs, easy to grep                              |
| Package manager      | `uv`                             | See [[stack-package-manager]]                                        |
| Containerization     | Docker Compose                   | `api + worker + postgres + redis` in one command                     |

### Bad — mixing in alternates without reason

```toml
# ❌ Don't pull in Celery alongside Arq
dependencies = ["arq", "celery"]
```

```python
# ❌ Don't use sync SQLAlchemy in async FastAPI routes
from sqlalchemy.orm import Session  # blocks the event loop
```

### Good — single choice per concern

```toml
dependencies = [
  "fastapi",
  "uvicorn[standard]",
  "pydantic",
  "pydantic-settings",
  "sqlalchemy[asyncio]",
  "asyncpg",
  "alembic",
  "pyjwt",
  "pwdlib[argon2]",
  "httpx",
  "redis",
  "arq",
  "langgraph",
  "langchain-core",
  "langchain-openai",
  "langchain-google-genai",
  "langchain-anthropic",
  "groq",
  "structlog",
]
```

### Notes for the README justification

- **FastAPI** chosen for async + Pydantic + WebSocket support
- **LangGraph** chosen because the visual workflow maps directly to graph nodes/edges, and it natively supports conditional branches and feedback loops required by the spec
- **Postgres + JSONB** keeps schema simple while storing graph JSON, tools config, memory config, guardrails
- **Redis + Arq** keeps long-running workflow execution off the request path without Celery overhead

See: [[stack-package-manager]], [[arch-modular-monolith]], [[avoid-overengineering]]
