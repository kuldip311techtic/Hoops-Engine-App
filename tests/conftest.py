"""Shared pytest fixtures."""

from __future__ import annotations

import os
import secrets
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

ROOT = Path(__file__).resolve().parents[1]


def _load_env_file(path: Path) -> None:
    """Load KEY=VALUE pairs with setdefault so process env still wins."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file(ROOT / ".env.test")
_load_env_file(ROOT / ".env")

os.environ["ENVIRONMENT"] = "test"


def _ensure_env(name: str) -> str:
    """Reuse an existing env value; otherwise generate a test-only token."""
    value = os.environ.get(name)
    if value:
        return value
    generated = secrets.token_urlsafe(32)
    os.environ[name] = generated
    return generated


def _as_asyncpg(url: str) -> str:
    """Normalize a Postgres URL to the async SQLAlchemy driver."""
    url = url.strip().strip('"').strip("'")
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://") :]
    return url


_ensure_env("JWT_SECRET_KEY")
os.environ.setdefault("JWT_SECRET", os.environ["JWT_SECRET_KEY"])
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")

_fallback_test_url = "postgresql+asyncpg://postgres:1234@localhost:5432/hoopsengine"
_test_url = _as_asyncpg(
    os.environ.get("TEST_DATABASE_URL")
    or os.environ.get("DATABASE_URL")
    or _fallback_test_url
)
os.environ["DATABASE_URL"] = _test_url
os.environ["TEST_DATABASE_URL"] = _test_url

from app.core.config import get_settings

get_settings.cache_clear()

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import hash_password
from app.dependencies.auth import get_auth_service
from app.dependencies.db import get_db
from app.main import app
from app.models.user import User, UserRole
from app.services.auth_service import AuthService
from tests.fakes import InMemoryUserRepository

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD") or f"Aa1!{secrets.token_hex(8)}"


async def _fake_db() -> AsyncIterator[MagicMock]:
    """Yield a session mock so HTTP tests never require live Postgres."""
    session = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock())
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    yield session


@pytest.fixture
def users() -> InMemoryUserRepository:
    """Empty in-memory user repository."""
    return InMemoryUserRepository()


@pytest.fixture
def admin_user(users: InMemoryUserRepository) -> User:
    """Seed a Super Admin used by in-memory login tests."""
    user = User(
        email=ADMIN_EMAIL,
        password_hash=hash_password(ADMIN_PASSWORD),
        role=UserRole.SUPER_ADMIN,
        token_version=1,
        is_active=True,
    )
    return users.add(user)


@pytest.fixture
def auth_service(users: InMemoryUserRepository) -> AuthService:
    """AuthService bound to in-memory users."""
    return AuthService(users)


@pytest.fixture
async def client(
    users: InMemoryUserRepository,
    admin_user: User,
) -> AsyncIterator[AsyncClient]:
    """HTTP client with in-memory auth and mocked database session."""

    def _auth_service() -> AuthService:
        return AuthService(users)

    app.dependency_overrides[get_db] = _fake_db
    app.dependency_overrides[get_auth_service] = _auth_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
