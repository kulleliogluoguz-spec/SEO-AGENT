"""
Database engine, session factory, and base model.
Uses SQLAlchemy 2.x async patterns throughout.
"""
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config.settings import get_settings

settings = get_settings()

# Naming convention for Alembic migrations
convention: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    metadata = metadata

    def to_dict(self) -> dict[str, Any]:
        """Convert model instance to dictionary."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


_connect_args = {"timeout": 5} if "asyncpg" in settings.database_url else {}

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.debug,
    future=True,
    connect_args=_connect_args,
    pool_pre_ping=True,
    pool_timeout=5,       # Don't wait >5s for a pool slot
    pool_recycle=300,     # Recycle connections every 5 min to prevent stale-socket hangs
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            try:
                await session.rollback()
            except Exception:
                pass
            raise
        finally:
            try:
                await session.close()
            except Exception:
                pass


async def check_db_connection() -> bool:
    """Health check: verify database connectivity."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
