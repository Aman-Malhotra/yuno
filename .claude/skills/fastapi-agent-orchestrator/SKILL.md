---
name: fastapi-agent-orchestrator
description: FastAPI + LangGraph + PostgreSQL + Redis + Arq backend architecture skill for the Yuno AI agent orchestration platform. Covers modular monolith layout, async SQLAlchemy, JWT auth, LangGraph runtime, Arq worker, WebSocket/Redis pub/sub for live monitoring, Telegram webhook channel, tool/LLM provider abstractions, and tests for critical paths. TRIGGER when writing, reviewing, or scaffolding any Python/FastAPI backend code for the Yuno agent orchestration platform (auth, agents, workflows, runs, runtime, channels, tools, llm providers, worker jobs, monitoring).
license: MIT
metadata:
  author: Aman Malhotra
  version: "1.0.0"
  project: yuno-ai-agent-orchestrator
---

# FastAPI Agent Orchestrator

Backend architecture rules for the Yuno AI Engineer Challenge — a **modular monolith** FastAPI app + Arq worker that runs LangGraph workflows, persists agent/run/message data in Postgres, streams live events over WebSocket via Redis pub/sub, and exposes a Telegram channel for human ↔ agent chat.

## When to Apply

Reference these rules when:

- Scaffolding the FastAPI backend
- Adding a new domain module (agent, workflow, run, channel, tool, provider)
- Choosing where logic goes (router vs service vs repository)
- Wiring auth, dependencies, or middleware
- Implementing the LangGraph runtime / workflow compiler
- Writing Arq jobs or wiring the worker process
- Streaming runtime events to the UI
- Implementing Telegram/Slack webhooks
- Adding a new LLM provider or tool
- Writing tests for critical paths

## Yuno Challenge Mapping

| Challenge requirement                          | Rule(s)                                                                  |
|------------------------------------------------|--------------------------------------------------------------------------|
| Agent CRUD (name, role, prompt, model, tools)  | `module-domain-layout`, `arch-layering-separation`                       |
| Agent config (schedules, memory, guardrails)   | `db-schema-jsonb`, `module-domain-layout`                                |
| Visual workflow builder (conditions, loops)    | `runtime-workflow-compiler`                                              |
| Real runtime executes agent logic              | `runtime-workflow-compiler`, `runtime-agent-executor`                    |
| Async agent-to-agent communication             | `worker-arq-setup`, `runtime-agent-executor`                             |
| Persisted message history visible in UI        | `db-async-sqlalchemy`, `module-domain-layout`                            |
| External channel (Telegram/Slack/WhatsApp)     | `channel-webhook-and-providers`, `worker-job-boundary`                   |
| Live monitoring (logs, messages, token/cost)   | `realtime-websocket-redis-pubsub`, `realtime-event-schema`, `runtime-event-emission` |
| Single-command local setup                     | `ops-docker-compose`, `ops-settings-pydantic`                            |
| Tests for critical paths                       | `test-critical-paths`, `test-async-httpx-client`                         |
| Justified runtime/stack choice in README       | `stack-choices`, `avoid-overengineering`                                 |

## Rule Categories by Priority

| Priority | Category               | Impact   | Prefix       |
|----------|------------------------|----------|--------------|
| 1        | Stack                  | CRITICAL | `stack-`     |
| 2        | Architecture           | CRITICAL | `arch-`, `module-` |
| 3        | API layer              | CRITICAL | `api-`       |
| 4        | Database               | CRITICAL | `db-`        |
| 5        | Auth                   | CRITICAL | `auth-`      |
| 6        | Runtime (LangGraph)    | CRITICAL | `runtime-`   |
| 7        | Worker (Arq)           | HIGH     | `worker-`    |
| 8        | Realtime               | HIGH     | `realtime-`  |
| 9        | Channels               | HIGH     | `channel-`   |
| 10       | Tools + LLM providers  | HIGH     | `tool-`, `llm-` |
| 11       | Testing                | HIGH     | `test-`      |
| 12       | Ops / config           | MEDIUM   | `ops-`       |
| 13       | Types                  | CRITICAL | `types-`     |
| 14       | Discipline             | MEDIUM   | `avoid-`     |

## Quick Reference

### 1. Stack (CRITICAL)

- `stack-choices` — FastAPI + LangGraph + Postgres + Redis + Arq + async SQLAlchemy + Pydantic v2 + JWT + httpx + pytest
- `stack-package-manager` — uv + `pyproject.toml`, no requirements.txt

### 2. Architecture (CRITICAL)

- `arch-modular-monolith` — one API service + one worker, never microservices for this scope
- `arch-project-structure` — `app/{core,db,api,modules,worker,tests}` layout
- `arch-layering-separation` — API layer → service layer → repository layer; never skip layers
- `module-domain-layout` — every domain owns `models.py / schemas.py / repository.py / service.py / router.py`

### 3. API layer (CRITICAL)

- `api-versioning-router` — `/api/v1/...`; routers only compose, never hold logic
- `api-response-shapes` — `PageResponse[T]` for lists; standard error envelope
- `api-error-handling` — typed app exceptions + global exception handler
- `api-dependency-injection` — FastAPI `Depends`, not a heavy DI container
- `api-openapi-spec-standard` — every route declares response_model/status_code/summary/responses/operation_id; BearerAuth scheme; error envelope as a component

### 4. Database (CRITICAL)

- `db-async-sqlalchemy` — SQLAlchemy 2.0 async + asyncpg only
- `db-session-lifecycle` — session per request via `get_db_session`; never global
- `db-alembic-migrations` — every schema change ships a migration
- `db-schema-jsonb` — JSONB for graph_json, tools_config, memory_config, guardrails, payloads

### 5. Auth (CRITICAL)

- `auth-jwt-and-refresh` — short-lived access + opaque refresh token (hashed in DB)
- `auth-password-hashing` — pwdlib[argon2]; never roll your own
- `auth-current-user-dep` — single `get_current_user` dependency on every protected route

### 6. Runtime (CRITICAL — product core)

- `runtime-workflow-compiler` — pure function: workflow JSON → LangGraph `StateGraph`
- `runtime-event-emission` — every node emits typed events; persist + publish in one path
- `runtime-agent-executor` — agent node = LLM call + tool loop + memory hooks; no HTTP code here

### 7. Worker (HIGH)

- `worker-arq-setup` — single `WorkerSettings`; jobs are async functions
- `worker-job-boundary` — API enqueues, worker executes; workflows never run inside a request handler

### 8. Realtime (HIGH)

- `realtime-websocket-redis-pubsub` — worker publishes to `run:{run_id}`; API WS subscribes and fans out
- `realtime-event-schema` — `RuntimeEvent` Pydantic model is the contract; same shape on disk, wire, and UI

### 9. Channels (HIGH)

- `channel-webhook-and-providers` — webhook handler only enqueues; channel provider implements a shared interface

### 10. Tools + LLM providers (HIGH)

- `tool-registry-interface` — every tool implements `Tool` ABC; registered by name
- `llm-provider-abstraction` — every provider implements `LLMProvider` ABC; routed by `model_provider` field

### 11. Testing (HIGH)

- `test-critical-paths` — auth, agent create, workflow validate+execute, runtime event persisted, channel webhook enqueue
- `test-async-httpx-client` — `httpx.AsyncClient` against the ASGI app; one test DB session per test

### 12. Ops (MEDIUM)

- `ops-docker-compose` — `api + worker + postgres + redis`; one `docker compose up --build`
- `ops-settings-pydantic` — `pydantic-settings` + `.env`; no `os.environ` reads scattered
- `ops-logging-and-request-id` — structlog + request-id middleware

### 13. Types (CRITICAL)

- `types-strict` — `mypy --strict`, every variable / arg / return / class attr / collection is explicitly typed; `Any` only at JSONB boundaries

### 14. Discipline (MEDIUM)

- `avoid-overengineering` — no microservices, no Kafka, no custom auth framework, no half-built providers

## How to Use

Each rule file contains:

- One-line statement of the rule
- Why it matters in the Yuno context
- Bad / good code examples (Python)
- Cross-references to related rules

Read a rule:

```
rules/arch-project-structure.md
rules/runtime-workflow-compiler.md
rules/realtime-websocket-redis-pubsub.md
```

## Target Folder Structure

The architecture rules collectively produce this layout. Use it as the starting skeleton:

```txt
backend/
  pyproject.toml
  alembic.ini
  Dockerfile
  README.md

  app/
    main.py

    core/
      config.py
      security.py
      logging.py
      errors.py
      constants.py
      lifespan.py

    db/
      base.py
      session.py
      migrations/
      models.py

    api/
      deps.py
      router.py
      v1/
        router.py
        auth.py
        users.py
        agents.py
        workflows.py
        workflow_runs.py
        messages.py
        tools.py
        llm_providers.py
        channels.py
        monitoring.py

    modules/
      auth/
      users/
      agents/
      workflows/
      runs/
      messages/
      tools/
      llm/
      channels/
      runtime/
      monitoring/

    worker/
      arq_app.py
      jobs.py
      schedules.py

    tests/
      conftest.py
      test_auth.py
      test_agent_creation.py
      test_workflow_execution.py
      test_message_delivery.py
```

Every `modules/<domain>/` follows the same internal layout — see `module-domain-layout`.
