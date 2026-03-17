"""
Alembic environment for async SQLAlchemy migrations.

Supports both offline (SQL generation) and online (live DB) migration.
Uses DATABASE_URL from settings, falling back to alembic.ini for offline mode.
"""
import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import all models so Alembic detects schema changes
from app.core.db.database import Base
import app.models.models  # noqa: F401 — registers all ORM models

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Get database URL from env var, falling back to alembic.ini."""
    url = os.environ.get("DATABASE_URL", "")
    if url:
        # asyncpg URL → use psycopg2 for sync Alembic operations
        return url.replace("postgresql+psycopg2://", "postgresql://")
    return config.get_main_option("sqlalchemy.url", "")


def run_migrations_offline() -> None:
    """Generate SQL without a live database connection."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations via async engine (psycopg2 for compatibility)."""
    url = get_url()
    # Use psycopg2 sync driver for migrations (asyncpg doesn't work with Alembic directly)
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
