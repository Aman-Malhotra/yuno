---
title: One-Command Local Setup via Docker Compose
impact: MEDIUM
impactDescription: The spec mandates "must run fully local with a single setup command"
tags: ops, docker, compose
---

## One-Command Local Setup via Docker Compose

`docker compose up --build` brings up the entire stack: API, worker, Postgres, Redis.

### `docker-compose.yml`

```yaml
services:
  api:
    build: ./backend
    command: >
      sh -c "uv run alembic upgrade head &&
             uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app

  worker:
    build: ./backend
    command: uv run arq app.worker.arq_app.WorkerSettings
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    volumes:
      - ./backend:/app

  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: agent
      POSTGRES_PASSWORD: agent
      POSTGRES_DB: agent_orchestrator
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U agent"]
      interval: 5s
      timeout: 3s
      retries: 10

  redis:
    image: redis:7
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

### `Dockerfile` (single image, two commands)

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

# default command overridden by docker-compose per service
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `.env.example`

```bash
# Database
DATABASE_URL=postgresql+asyncpg://agent:agent@postgres:5432/agent_orchestrator

# Redis
REDIS_URL=redis://redis:6379/0

# JWT
JWT_SECRET_KEY=change-me-in-prod
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS — comma-separated origins
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# LLM providers (optional — provider registered if key is set)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
GROQ_API_KEY=

# Telegram (optional)
TELEGRAM_BOT_TOKEN=
TELEGRAM_WEBHOOK_SECRET=
```

The README's setup section is exactly:

```bash
cp .env.example .env
# fill in TELEGRAM_BOT_TOKEN and at least one LLM key
docker compose up --build
```

### Why bind-mount `./backend` in dev

Hot reload (`uvicorn --reload`) needs to see file changes. For a production image, drop the volume + the `--reload`.

### Migrations on every boot

The `api` command runs `alembic upgrade head` before launching uvicorn. Safe to do repeatedly — Alembic is idempotent. The `worker` doesn't run migrations; it'd race with the API.

### Bad — running migrations from a sidecar that may finish after the API starts

```yaml
# ❌ API starts before migrations finish; first requests hit a missing table
migrate:
  build: ./backend
  command: uv run alembic upgrade head
```

### Bad — exposing Postgres without a password in production

For the assignment, fine. For real deploys, override via `.env` and remove the `ports:` mapping.

### Rules

- Single command: `docker compose up --build`
- API container runs migrations before uvicorn
- Worker is a separate service, same image, different command
- All env reads happen through `core/config.py` — see [[ops-settings-pydantic]]
- Healthcheck on Postgres + `depends_on: condition: service_healthy` so the API doesn't race startup

See: [[stack-package-manager]], [[ops-settings-pydantic]], [[db-alembic-migrations]]
