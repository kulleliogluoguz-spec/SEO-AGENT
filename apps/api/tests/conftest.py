"""
Pytest configuration and shared fixtures for all backend tests.

Database strategy:
  - Uses PostgreSQL for integration tests (when DATABASE_URL env var points to PG)
  - Uses SQLite for unit/fast tests, but ONLY for tables that don't use
    PostgreSQL-specific types.
  - Most unit tests mock the DB entirely and don't need a real engine.

IMPORTANT: SQLite does NOT support JSONB, UUID(as_uuid=True), or other PG types.
For tests that need the DB, we use a PostgreSQL-compatible test DB or patch
the column types. The approach here is to use a separate test-compatible model
layer that maps JSONB→JSON and UUID→String for SQLite runs.
"""
import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import JSON, String, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.db.database import Base, get_db
from app.core.security.auth import create_access_token, hash_password
from app.main import app
from app.models.models import MemberRole, Membership, Organization, Site, SiteStatus, User, Workspace

# ─── Test Database Configuration ─────────────────────────────────────────────

# Use SQLite for tests (fast, no external DB required)
# We patch JSONB → JSON and UUID → String at the dialect level via events.
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    # SQLite needs this for async
    connect_args={"check_same_thread": False},
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# ─── SQLite Compatibility Patch ───────────────────────────────────────────────
# Replace PostgreSQL-specific types with SQLite-compatible equivalents
# This is applied once at module load for the test run.

from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy import event
from sqlalchemy.engine import Engine


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable WAL mode and foreign keys for SQLite test runs."""
    if "sqlite" in str(dbapi_connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def _patch_columns_for_sqlite(metadata) -> None:
    """
    Walk all columns and replace JSONB with JSON, UUID with String(36).
    This is a one-time patch applied before create_all for SQLite tests.
    """
    for table in metadata.tables.values():
        for col in table.columns:
            if isinstance(col.type, PGUUID):
                col.type = String(36)
            elif isinstance(col.type, JSONB):
                col.type = JSON()


_patch_columns_for_sqlite(Base.metadata)


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Single event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Fresh in-memory SQLite database per test function."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client wired to the test SQLite database."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def demo_user(db_session: AsyncSession) -> User:
    """Create a test user with org + workspace."""
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="test@example.com",
        hashed_password=hash_password("TestPass1!"),
        full_name="Test User",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)

    org = Organization(
        id=uuid.uuid4(),
        name="Test Org",
        slug=f"test-org-{user_id.hex[:8]}",
    )
    db_session.add(org)
    await db_session.flush()

    db_session.add(Membership(
        id=uuid.uuid4(),
        user_id=user.id,
        organization_id=org.id,
        role=MemberRole.OWNER,
    ))

    workspace = Workspace(
        id=uuid.uuid4(),
        organization_id=org.id,
        name="Test Workspace",
        slug="test-workspace",
        autonomy_level=1,
    )
    db_session.add(workspace)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(demo_user: User) -> dict[str, str]:
    """JWT Authorization headers for demo_user."""
    token = create_access_token(str(demo_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def demo_site(db_session: AsyncSession, demo_user: User) -> Site:
    """Create a test site attached to the demo workspace."""
    from sqlalchemy import select
    ws = (await db_session.execute(select(Workspace).where(Workspace.slug == "test-workspace"))).scalar_one()

    site = Site(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        url="https://test-example.com",
        domain="test-example.com",
        name="Test Site",
        status=SiteStatus.ACTIVE,
    )
    db_session.add(site)
    await db_session.commit()
    await db_session.refresh(site)
    return site


@pytest_asyncio.fixture
async def superuser(db_session: AsyncSession) -> User:
    """Create a superuser for admin endpoint tests."""
    user = User(
        id=uuid.uuid4(),
        email="admin@test.com",
        hashed_password=hash_password("AdminPass1!"),
        full_name="Admin User",
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def superuser_headers(superuser: User) -> dict[str, str]:
    token = create_access_token(str(superuser.id))
    return {"Authorization": f"Bearer {token}"}
