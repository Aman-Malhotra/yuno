---
title: One Typed Settings Object via `pydantic-settings`
impact: MEDIUM
impactDescription: One typed object means no `os.environ.get()` strewn across the codebase and no string/None footguns
tags: ops, config, settings
---

## One Typed Settings Object via `pydantic-settings`

All env config lives in `app/core/config.py`. Anywhere else that reads env directly is a bug.

### The settings class

```python
# app/core/config.py
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Agent Orchestrator"
    environment: str = "local"

    # Database
    database_url: str

    # Redis
    redis_url: str

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # CORS — accept comma-separated string in env, expose as list[str]
    cors_origins: list[str] = Field(default_factory=list)

    # LLM providers (optional)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    groq_api_key: str | None = None

    # Telegram (optional)
    telegram_bot_token: str | None = None
    telegram_webhook_secret: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()   # imported as `from app.core.config import settings`
```

`pydantic-settings` auto-parses comma-separated strings into `list[str]` when the field is typed as such.

### Usage

```python
# ✅ Anywhere in the app
from app.core.config import settings

engine = create_async_engine(settings.database_url)
```

### Bad — `os.environ` reads scattered

```python
# ❌ Untyped, no default, fails late, hard to discover
import os
DB_URL = os.environ["DATABASE_URL"]
JWT_SECRET = os.environ.get("JWT_SECRET", "")
```

### Bad — module-level `getenv` with side-effect defaults

```python
# ❌ Imports become order-sensitive
JWT_SECRET = os.getenv("JWT_SECRET_KEY") or "dev-only"
```

### Bad — booleans / lists parsed by hand

```python
# ❌ pydantic-settings already does this
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
CORS = os.getenv("CORS", "").split(",")
```

### Tests + multiple environments

For tests, override at instance level — don't write a parallel `TestSettings` class:

```python
# tests/conftest.py
import os

os.environ["DATABASE_URL"] = "postgresql+asyncpg://agent:agent@localhost:5432/agent_test"
os.environ["JWT_SECRET_KEY"] = "test-secret"
```

…**before** importing `app.core.config`. Or use `pytest-env`.

### Required vs optional

- Required (no default) → fail-fast at startup if missing. Use for `database_url`, `redis_url`, `jwt_secret_key`.
- Optional (`| None = None`) → the relevant provider/integration just isn't registered. Use for LLM keys + Telegram.

### Rules

- One `Settings` class, one module-level `settings` instance
- Anything outside `core/config.py` that calls `os.environ`, `os.getenv`, or `dotenv` is a bug
- Optional integrations are gated on `if settings.<key>:` in their registry builder
- `.env.example` lists every var with safe placeholders

See: [[ops-docker-compose]], [[channel-webhook-and-providers]], [[llm-provider-abstraction]]
