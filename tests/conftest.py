"""Shared pytest fixtures for PostgreSQL-backed integration tests."""

import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# ---------------------------------------------------------------------------
# Environment — read from .env.test / environment; never hardcode secrets.
# ---------------------------------------------------------------------------
from app.core.config import normalize_database_url

_TEST_ENV_FILE = Path(__file__).resolve().parent.parent / ".env.test"
if _TEST_ENV_FILE.exists():
    for _line in _TEST_ENV_FILE.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _key, _value = _line.split("=", 1)
        os.environ.setdefault(_key.strip(), _value.strip())

_raw_db_url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
if _raw_db_url is None:
    raise RuntimeError("TEST_DATABASE_URL or DATABASE_URL must be set (see .env.test).")
TEST_DATABASE_URL = normalize_database_url(_raw_db_url)
if not TEST_DATABASE_URL:
    raise RuntimeError("Database URL is empty after normalization.")

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["TEST_DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("SECRET_KEY", "test-secret-key-min-16-chars")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-min-32-chars!!")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("LOG_LEVEL", "WARNING")

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password
from app.db import session as db_session_module
from app.db.base import Base
from app.dependencies.database import get_db
from app.main import create_app
from app.models.organization import Organization  # noqa: F401
from app.models.super_admin import SuperAdmin
from app.models.support_request import SupportRequest  # noqa: F401
from app.models.user import User  # noqa: F401

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


@pytest.fixture(scope="session")
def test_users() -> dict[str, dict[str, Any]]:
    """Return the five test user persona definitions."""
    return TEST_USER_DEFINITIONS


@pytest_asyncio.fixture(scope="session")
async def test_engine() -> AsyncIterator[AsyncEngine]:
    """Session-scoped async engine bound to the pytest session event loop."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def test_session_factory(
    test_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Session-scoped session factory sharing the session event loop."""
    return async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )


async def _truncate_super_admins(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Remove Super Admin, user, organization, and support request rows."""
    async with session_factory() as session, session.begin():
        await session.execute(
            text(
                "TRUNCATE TABLE support_requests, users, organizations, "
                "super_admins RESTART IDENTITY CASCADE"
            )
        )


async def _seed_super_admins(
    session_factory: async_sessionmaker[AsyncSession],
) -> list[SuperAdmin]:
    """Insert four Super Admin rows (excludes 'new' persona)."""
    admins: list[SuperAdmin] = []
    async with session_factory() as session:
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
async def seeded_super_admins(
    test_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[list[SuperAdmin]]:
    """Truncate and re-seed Super Admin rows before each test."""
    await _truncate_super_admins(test_session_factory)
    admins = await _seed_super_admins(test_session_factory)
    yield admins
    await _truncate_super_admins(test_session_factory)


@pytest_asyncio.fixture
async def db_session(
    seeded_super_admins: list[SuperAdmin],
    test_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Yield a database session bound to the test PostgreSQL database."""
    async with test_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(
    seeded_super_admins: list[SuperAdmin],
    test_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncClient]:
    """HTTP client with get_db overridden to use the test database session."""
    db_session_module._engine = None
    db_session_module._session_factory = None
    db_session_module._test_engine = None
    db_session_module._test_session_factory = None

    application = create_app()

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with test_session_factory() as session:
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
def auth_tokens(
    test_users: dict,
    seeded_super_admins: list[SuperAdmin],
) -> dict[str, str]:
    """JWT access tokens whose sub matches seeded Super Admin UUIDs."""
    by_email = {admin.email: admin for admin in seeded_super_admins}
    tokens: dict[str, str] = {}
    for key, data in test_users.items():
        if data.get("seed", True) is False:
            continue
        admin = by_email[data["email"]]
        tokens[key] = create_access_token(
            subject=str(admin.id),
            claims={"email": admin.email, "role": "super_admin"},
        )
    return tokens
