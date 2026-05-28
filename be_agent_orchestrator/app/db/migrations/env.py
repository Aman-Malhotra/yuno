import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.db.base import Base

# Import each module's models here so Alembic autogenerate sees them.
from app.modules.agents import models as _agents  # noqa: F401
from app.modules.audit import models as _audit  # noqa: F401
from app.modules.channels import models as _channels  # noqa: F401
from app.modules.llm import models as _llm  # noqa: F401
from app.modules.memory import models as _memory  # noqa: F401
from app.modules.messages import models as _messages  # noqa: F401
from app.modules.runs import models as _runs  # noqa: F401
from app.modules.schedules import models as _schedules  # noqa: F401
from app.modules.tools import models as _tools  # noqa: F401
from app.modules.users import models as _users  # noqa: F401
from app.modules.webhooks import models as _webhooks  # noqa: F401
from app.modules.workflows import models as _workflows  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def do_run_migrations(connection: Connection) -> None:
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


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
