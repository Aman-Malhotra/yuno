---
title: Use uv as the Package Manager
impact: CRITICAL
impactDescription: One package manager, one lockfile — keeps local + Docker + CI reproducible
tags: stack, uv, pyproject
---

## Use uv as the Package Manager

All dependency management goes through **uv** + `pyproject.toml` + `uv.lock`. No `requirements.txt`, no `pip install` ad-hoc, no Poetry.

### Why

- Fast resolution, single lockfile
- Native `[dependency-groups]` for dev dependencies
- Same commands work locally, in Docker, in CI

### Bad

```bash
# ❌ Mixing managers — pip writes a different lock than uv
pip install fastapi
pip freeze > requirements.txt
```

```dockerfile
# ❌ Docker installing from requirements.txt while local uses uv.lock
RUN pip install -r requirements.txt
```

### Good

`pyproject.toml`:

```toml
[project]
name = "agent-orchestrator-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "fastapi",
  "uvicorn[standard]",
  "pydantic",
  "pydantic-settings",
  "email-validator",
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

[dependency-groups]
dev = [
  "pytest",
  "pytest-asyncio",
  "ruff",
  "mypy",
  "pre-commit",
  "httpx",
  "testcontainers",
  "factory-boy",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.mypy]
python_version = "3.11"
strict = true
```

Commands:

```bash
uv sync                       # install everything
uv sync --group dev           # include dev deps
uv add httpx                  # add a runtime dep
uv add --group dev pytest     # add a dev dep
uv run uvicorn app.main:app   # run with project env
uv run pytest                 # run tests
```

Dockerfile:

```dockerfile
FROM python:3.11-slim

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Rules

- Commit `uv.lock` to git
- Never edit `pyproject.toml` deps by hand for adds/removes — use `uv add` / `uv remove`
- Dev-only deps go in `[dependency-groups].dev`, never in `[project].dependencies`

See: [[stack-choices]], [[ops-docker-compose]]
