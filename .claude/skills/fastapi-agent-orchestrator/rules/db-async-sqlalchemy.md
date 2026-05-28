---
title: SQLAlchemy 2.0 Async + asyncpg Only
impact: CRITICAL
impactDescription: Sync SQLAlchemy blocks the event loop in FastAPI; mixing styles guarantees subtle bugs
tags: db, sqlalchemy, async
---

## SQLAlchemy 2.0 Async + asyncpg Only

The entire stack is async — the database layer must match.

### Engine + session

```python
# app/db/session.py
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

`database_url` must use the async driver:

```bash
DATABASE_URL=postgresql+asyncpg://agent:agent@postgres:5432/agent_orchestrator
```

### Declarative base

```python
# app/db/base.py
from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


def new_id() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class IdMixin:
    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=new_id,
    )
```

### Repository pattern

```python
# app/modules/agents/repository.py
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Agent


class AgentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_by_user(
        self, user_id: str, page: int, page_size: int
    ) -> tuple[list[Agent], int]:
        offset = (page - 1) * page_size

        items_q = (
            select(Agent)
            .where(Agent.user_id == user_id)
            .order_by(Agent.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        total_q = select(func.count(Agent.id)).where(Agent.user_id == user_id)

        items = list((await self.db.execute(items_q)).scalars())
        total = (await self.db.execute(total_q)).scalar_one()
        return items, total
```

### Bad — sync `Session`

```python
# ❌ Blocks the event loop on every query
from sqlalchemy.orm import Session

def list_agents(db: Session):
    return db.query(Agent).all()
```

### Bad — global session

```python
# ❌ Sessions are not safe to share across requests
session = AsyncSessionLocal()
```

### Bad — Query API

```python
# ❌ Legacy 1.x style; use select() in 2.0
result = await db.query(Agent).filter_by(user_id=user_id).all()
```

### Good — 2.0 style + per-request session

```python
result = await db.execute(select(Agent).where(Agent.user_id == user_id))
agents = list(result.scalars())
```

### Rules

- Driver is always `postgresql+asyncpg`
- Use `select(...)`, not `query(...)`
- Models use `Mapped[...]` + `mapped_column(...)` (2.0 typed syntax)
- One session per request (or per job in the worker)
- `expire_on_commit=False` so returned ORM objects can be serialized after commit
- No global sessions, no module-level engine reuse hacks

See: [[db-session-lifecycle]], [[db-alembic-migrations]], [[module-domain-layout]]
