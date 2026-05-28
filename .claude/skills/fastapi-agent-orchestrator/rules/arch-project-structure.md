---
title: Project Structure
impact: CRITICAL
impactDescription: A single canonical layout means every new feature lands in an obvious place
tags: architecture, folder-structure
---

## Project Structure

```txt
backend/
  pyproject.toml
  alembic.ini
  Dockerfile
  README.md

  app/
    main.py                # FastAPI app factory + router mount + middleware

    core/                  # cross-cutting infrastructure
      config.py            # pydantic-settings
      security.py          # JWT + password hashing
      logging.py           # structlog setup
      errors.py            # app exception hierarchy
      constants.py
      lifespan.py          # startup / shutdown hooks

    db/
      base.py              # DeclarativeBase
      session.py           # async engine, sessionmaker, get_db_session
      migrations/          # alembic env + versions
      models.py            # optional aggregate import for alembic autogenerate

    api/                   # HTTP routing only
      deps.py              # shared dependencies (auth, db, services)
      router.py            # api_router composes v1
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
        monitoring.py      # WebSocket endpoint

    modules/               # one folder per domain — see module-domain-layout
      auth/
      users/
      agents/
      workflows/
      runs/
      messages/
      tools/
      llm/
      channels/
      runtime/             # LangGraph compiler + executor + events
      monitoring/          # WS connection manager + event publisher

    worker/
      arq_app.py           # WorkerSettings
      jobs.py              # async job functions
      schedules.py         # cron-style schedules

    tests/
      conftest.py
      test_auth.py
      test_agent_creation.py
      test_workflow_execution.py
      test_message_delivery.py
```

### Why these top-level folders

| Folder       | Role                                                                                                     |
|--------------|----------------------------------------------------------------------------------------------------------|
| `core/`      | Stuff every module uses: config, security, logging, errors                                               |
| `db/`        | Engine + session + migrations. No business logic.                                                        |
| `api/`       | HTTP transport only. Routers compose, never hold logic. See [[api-versioning-router]]                    |
| `modules/`   | Domain code. Each module owns its models/schemas/repo/service/router. See [[module-domain-layout]]       |
| `worker/`    | Arq entrypoint + jobs. Imports services from `modules/`, never the other way around.                     |
| `tests/`     | All tests. Mirror module names where useful.                                                             |

### Bad — layer-first folders

```txt
# ❌ Hard to find anything; god-folders
app/
  models/
    agent.py
    workflow.py
    user.py
  routers/
  services/
  schemas/
```

### Good — domain-first inside `modules/`

```txt
app/modules/agents/
  models.py
  schemas.py
  repository.py
  service.py
  router.py
```

### Import direction

```txt
api/  ──► modules/<domain>/service.py
worker/  ──► modules/<domain>/service.py
modules/<domain>/service.py  ──► modules/<domain>/repository.py
modules/<domain>/repository.py  ──► db/session.py + own models.py
```

Never:

- `db/` importing from `modules/`
- `modules/<A>/repository.py` importing `modules/<B>/repository.py` (cross-module access goes through `service.py`)
- `core/` importing from `modules/`

See: [[arch-modular-monolith]], [[arch-layering-separation]], [[module-domain-layout]]
