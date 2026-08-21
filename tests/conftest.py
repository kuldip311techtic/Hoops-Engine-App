"""Shared pytest fixtures. Environment is set before the app is imported."""

from __future__ import annotations

import os
import secrets
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

os.environ["ENVIRONMENT"] = "test"


def _ensure_env(name: str) -> str:
    """Reuse an existing env value; otherwise generate a test-only token."""
    value = os.environ.get(name)
    if value:
        return value
    generated = secrets.token_urlsafe(32)
    os.environ[name] = generated
    return generated


_ensure_env("JWT_SECRET_KEY")
os.environ.setdefault("JWT_SECRET", os.environ["JWT_SECRET_KEY"])
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://pytest@127.0.0.1:5432/hoopsengine",
)
os.environ.setdefault(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://pytest@127.0.0.1:5432/hoopsengine_test",
)
_ensure_env("AUTH0_WEBHOOK_SECRET")
_ensure_env("BILLING_WEBHOOK_SECRET")
os.environ.setdefault("AUTH0_DOMAIN", "prod.example.auth0.com")
os.environ.setdefault("AUTH0_SANDBOX_DOMAIN", "sandbox.example.auth0.com")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.dependencies.auth import get_auth_service  # noqa: E402
from app.dependencies.db import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402
from app.services.auth_service import AuthService  # noqa: E402
from tests.fakes import InMemorySubscriptionRepository, InMemoryUserRepository  # noqa: E402

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD") or f"Aa1!{secrets.token_hex(8)}"


async def _fake_db() -> AsyncIterator[MagicMock]:
    """Yield a session mock so tests never need a live Postgres checkout."""
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
def subscriptions() -> InMemorySubscriptionRepository:
    """Empty in-memory subscription repository."""
    return InMemorySubscriptionRepository()


@pytest.fixture
def admin_user(users: InMemoryUserRepository) -> User:
    """Seed a Super Admin used by login tests."""
    user = User(
        email=ADMIN_EMAIL,
        password_hash=hash_password(ADMIN_PASSWORD),
        role=UserRole.SUPER_ADMIN,
        token_version=1,
        is_active=True,
    )
    return users.add(user)


@pytest.fixture
def auth_service(
    users: InMemoryUserRepository,
    subscriptions: InMemorySubscriptionRepository,
) -> AuthService:
    """AuthService bound to in-memory repos."""
    return AuthService(users, subscriptions)


@pytest.fixture
async def client(
    users: InMemoryUserRepository,
    subscriptions: InMemorySubscriptionRepository,
    admin_user: User,
) -> AsyncIterator[AsyncClient]:
    """HTTP client against the FastAPI app with in-memory auth."""

    def _auth_service() -> AuthService:
        return AuthService(users, subscriptions)

    app.dependency_overrides[get_db] = _fake_db
    app.dependency_overrides[get_auth_service] = _auth_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
