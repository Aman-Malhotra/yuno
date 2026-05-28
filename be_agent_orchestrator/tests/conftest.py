"""Test fixtures.

Each test gets a fresh ``AsyncEngine`` with ``NullPool``. Reason:
pytest-asyncio creates a new event loop per test, but a pooled asyncpg
connection is bound to the loop it was created on — reusing it across
loops raises ``RuntimeError: Event loop is closed``. ``NullPool`` opens
and closes a connection per checkout, so nothing leaks across tests.
"""

from collections.abc import AsyncIterator, Awaitable, Callable

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.session import get_db_session
from app.main import app


@pytest_asyncio.fixture
async def test_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session_factory(
    test_engine: AsyncEngine,
) -> Callable[[], AsyncIterator[AsyncSession]]:
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

    async def _get_db_session() -> AsyncIterator[AsyncSession]:
        async with session_maker() as session:
            yield session

    return _get_db_session


@pytest_asyncio.fixture
async def client(
    db_session_factory: Callable[[], Awaitable[AsyncIterator[AsyncSession]]],
) -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_db_session] = db_session_factory
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
