"""Shared pytest fixtures for PostgreSQL-backed integration tests."""

import os
from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Environment — read from .env.test / environment; never hardcode secrets.
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:1234@localhost:5432/hoopsengine_test",
    ),
)

# Normalize accidental duplicated key prefixes (matches app.core.config validator).
for _prefix in ("DATABASE_URL=", "TEST_DATABASE_URL="):
    if TEST_DATABASE_URL.startswith(_prefix):
        TEST_DATABASE_URL = TEST_DATABASE_URL.removeprefix(_prefix)

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["TEST_DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("SECRET_KEY", "test-secret-key-min-16-chars")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-min-32-chars!!")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("LOG_LEVEL", "WARNING")

from app.core.config import get_settings  # noqa: E402
from app.core.security import create_access_token, hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_async_session  # noqa: E402
from app.dependencies.database import get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.super_admin import SuperAdmin  # noqa: E402

get_settings.cache_clear()

# ---------------------------------------------------------------------------
# Test user definitions (5 personas mapped to SuperAdmin model)
# ---------------------------------------------------------------------------
TEST_USER_DEFINITIONS: dict[str, dict[str, Any]] = {
    "admin": {
        "email": "admin@test.com",
        "password": "TestAdmin123!",
        "role": "super_admin",
        "is_active": True,
        "description": "Primary active Super Admin (admin equivalent)",
    },
    "user": {
        "email": "user@test.com",
        "password": "TestUser123!",
        "role": "super_admin",
        "is_active": True,
        "description": "Secondary active Super Admin (regular equivalent)",
    },
    "viewer": {
        "email": "viewer@test.com",
        "password": "TestViewer123!",
        "role": "super_admin",
        "is_active": True,
        "description": "Active Super Admin for read-oriented scenarios",
    },
    "inactive": {
        "email": "inactive@test.com",
        "password": "TestInactive123!",
        "role": "super_admin",
        "is_active": False,
        "description": "Deactivated Super Admin account",
    },
    "new": {
        "email": "newuser@test.com",
        "password": "NewUser123!",
        "role": "super_admin",
        "is_active": True,
        "description": "Credentials for not-yet-seeded user (login should fail)",
        "seed": False,
    },
}

_test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, pool_pre_ping=True)
_test_session_factory = async_sessionmaker(
    bind=_test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


@pytest.fixture(scope="session")
def test_users() -> dict[str, dict[str, Any]]:
    """Return the five test user persona definitions."""
    return TEST_USER_DEFINITIONS


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database() -> AsyncIterator[None]:
    """Create tables once for the test session; drop on teardown."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _test_engine.dispose()


async def _truncate_super_admins() -> None:
    """Remove all rows from super_admins without dropping schema."""
    async with _test_engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE super_admins RESTART IDENTITY CASCADE"))


async def _seed_super_admins() -> list[SuperAdmin]:
    """Insert four Super Admin rows (excludes 'new' persona)."""
    admins: list[SuperAdmin] = []
    async with _test_session_factory() as session:
        for key, data in TEST_USER_DEFINITIONS.items():
            if data.get("seed", True) is False:
                continue
            admin = SuperAdmin(
                email=data["email"],
                hashed_password=hash_password(data["password"]),
                is_active=data["is_active"],
            )
            session.add(admin)
            admins.append(admin)
        await session.commit()
        for admin in admins:
            await session.refresh(admin)
    return admins


@pytest_asyncio.fixture
async def seeded_super_admins() -> AsyncIterator[list[SuperAdmin]]:
    """Truncate and re-seed Super Admin rows before each test."""
    await _truncate_super_admins()
    admins = await _seed_super_admins()
    yield admins
    await _truncate_super_admins()


@pytest_asyncio.fixture
async def db_session(seeded_super_admins: list[SuperAdmin]) -> AsyncIterator[AsyncSession]:
    """Yield a database session bound to the test PostgreSQL database."""
    async with _test_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(seeded_super_admins: list[SuperAdmin]) -> AsyncIterator[AsyncClient]:
    """HTTP client with get_db overridden to use the test database session."""
    application = create_app()

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with _test_session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    application.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    application.dependency_overrides.clear()


@pytest.fixture
def auth_tokens(test_users: dict) -> dict[str, str]:
    """Pre-generated JWT access tokens for each seeded persona (except new)."""
    tokens: dict[str, str] = {}
    for key, data in test_users.items():
        if data.get("seed", True) is False:
            continue
        tokens[key] = create_access_token(
            subject=f"test-{key}-id",
            claims={"email": data["email"], "role": "super_admin"},
        )
    return tokens
