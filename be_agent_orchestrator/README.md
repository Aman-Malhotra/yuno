# be_agent_orchestrator

Yuno AI Agent Orchestration Platform — backend.

Stack: FastAPI · LangGraph · PostgreSQL · Redis · Arq · SQLAlchemy 2.0 async · Alembic · Pydantic v2 · structlog. Managed with `uv`.

## Run

```bash
cp .env.example .env
# fill in TELEGRAM_BOT_TOKEN and at least one LLM key
docker compose up --build
```

Ports (host = container):

| Service  | Port |
|----------|------|
| API      | 3001 |
| Postgres | 3002 |
| Redis    | 3003 |

API: <http://localhost:3001> · Docs: <http://localhost:3001/docs>

## Layout

```
app/
  main.py             FastAPI app factory
  core/               config, security, logging, errors, lifespan, middleware
  db/                 SQLAlchemy engine + session + Alembic migrations
  api/                versioned router composition
    v1/router.py      mounts module routers under /api/v1
  modules/            domain modules (models / schemas / repository / service / router)
    auth, users, agents, workflows, runs, messages,
    tools, llm, channels, runtime, monitoring
  worker/             Arq worker entrypoint + jobs
tests/                pytest + httpx.AsyncClient
```

## Local dev (without Docker)

```bash
uv sync --group dev
uv run alembic upgrade head
uv run uvicorn app.main:app --host 0.0.0.0 --port 3001 --reload
# in another shell
uv run arq app.worker.arq_app.WorkerSettings
```

`DATABASE_URL` / `REDIS_URL` in `.env` reference the docker service names. For host-side runs, point them at `localhost:3002` and `localhost:3003`.

## Tests

```bash
uv run pytest
```
