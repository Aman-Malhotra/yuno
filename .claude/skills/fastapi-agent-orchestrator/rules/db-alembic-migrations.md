---
title: Every Schema Change Ships a Migration
impact: CRITICAL
impactDescription: No `create_all()` in production paths — the only way to evolve schema is Alembic, so dev/CI/Docker all stay in sync
tags: db, alembic, migrations
---

## Every Schema Change Ships a Migration

Schema is owned by Alembic. `Base.metadata.create_all()` is fine in tests; it must **not** run in app startup.

### Layout

```txt
backend/
  alembic.ini
  app/db/migrations/
    env.py
    script.py.mako
    versions/
      20260101_0001_initial.py
      20260102_0001_add_runtime_events.py
```

### `alembic.ini` essentials

```ini
[alembic]
script_location = app/db/migrations
sqlalchemy.url = postgresql+asyncpg://agent:agent@postgres:5432/agent_orchestrator
```

The URL also gets overridden in `env.py` from settings — see below.

### Async `env.py`

```python
# app/db/migrations/env.py
import asyncio
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool
from alembic import context

from app.core.config import settings
from app.db.base import Base

# Import every module's models so autogenerate sees them.
from app.modules.users import models as _users  # noqa: F401
from app.modules.agents import models as _agents  # noqa: F401
from app.modules.workflows import models as _workflows  # noqa: F401
from app.modules.runs import models as _runs  # noqa: F401
from app.modules.messages import models as _messages  # noqa: F401
from app.modules.channels import models as _channels  # noqa: F401


config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section) or {},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


asyncio.run(run_migrations_online())
```

### Workflow

```bash
uv run alembic revision --autogenerate -m "add agents table"
uv run alembic upgrade head
uv run alembic downgrade -1   # for local debugging
```

In Docker, migrations run before the API starts. See [[ops-docker-compose]].

### Rules

- Never call `Base.metadata.create_all(engine)` outside of `tests/`
- Every PR that changes a model includes the matching migration
- Migrations are reviewed like code — name them with intent (`add_runtime_events`, not `0042`)
- `__init__.py` of `app/db/models.py` re-exports module models so autogenerate sees everything

### Bad

```python
# ❌ Bypasses Alembic, hides schema drift
@app.on_event("startup")
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

### Good — startup runs migrations, not create_all

```bash
# docker-compose api command
sh -c "uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"
```

See: [[db-async-sqlalchemy]], [[ops-docker-compose]]
