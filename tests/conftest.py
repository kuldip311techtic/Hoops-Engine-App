"""Shared pytest fixtures: in-memory unit fakes plus real PostgreSQL for live API tests."""

from __future__ import annotations

import os
import secrets
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

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
_ensure_env("AUTH0_WEBHOOK_SECRET")
_ensure_env("BILLING_WEBHOOK_SECRET")
os.environ.setdefault("AUTH0_DOMAIN", "prod.example.auth0.com")
os.environ.setdefault("AUTH0_SANDBOX_DOMAIN", "sandbox.example.auth0.com")
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
from sqlalchemy import text

from app.core.security import create_access_token, hash_password
from app.dependencies.auth import get_auth_service
from app.dependencies.db import get_db
from app.main import app
from app.models.user import User, UserRole
from app.services.auth_service import AuthService
from tests.fakes import (
    InMemorySubscriptionRepository,
    InMemoryUserRepository,
)

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD") or f"Aa1!{secrets.token_hex(8)}"

LIVE_ADMIN_EMAIL = "admin@test.com"
LIVE_ADMIN_PASSWORD = os.environ.get("TEST_LIVE_ADMIN_PASSWORD") or f"TestAdmin{secrets.token_hex(4)}!"
LIVE_USER_EMAIL = "user@test.com"
LIVE_USER_PASSWORD = os.environ.get("TEST_LIVE_USER_PASSWORD") or f"TestUser{secrets.token_hex(4)}!"
LIVE_VIEWER_EMAIL = "viewer@test.com"
LIVE_VIEWER_PASSWORD = os.environ.get("TEST_LIVE_VIEWER_PASSWORD") or f"TestViewer{secrets.token_hex(4)}!"
LIVE_INACTIVE_EMAIL = "inactive@test.com"
LIVE_INACTIVE_PASSWORD = os.environ.get("TEST_LIVE_INACTIVE_PASSWORD") or f"TestInactive{secrets.token_hex(4)}!1"
LIVE_NEW_EMAIL = "newuser@test.com"
LIVE_NEW_PASSWORD = os.environ.get("TEST_LIVE_NEW_PASSWORD") or f"NewUser{secrets.token_hex(4)}!1"

_HASH_CACHE: dict[str, str] = {}


def _cached_hash(plain: str) -> str:
    """Hash once per unique password for faster seeding."""
    if plain not in _HASH_CACHE:
        _HASH_CACHE[plain] = hash_password(plain)
    return _HASH_CACHE[plain]


async def _fake_db() -> AsyncIterator[MagicMock]:
    """Yield a session mock so in-memory HTTP tests never need live Postgres."""
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


@pytest.fixture(scope="session")
def postgres_schema() -> None:
    """Apply Alembic migrations (then create_all) to the PostgreSQL test database."""
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine

    from app.db.base import Base
    from app.models import Organization, Subscription, SubscriptionPlan, User  # noqa: F401

    cfg = Config(str(ROOT / "alembic.ini"))
    command.upgrade(cfg, "head")
    sync_url = os.environ["TEST_DATABASE_URL"].replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_url)
    Base.metadata.create_all(engine)
    engine.dispose()


@pytest.fixture
async def seeded_users(postgres_schema: None) -> AsyncIterator[dict[str, User]]:
    """Insert admin, user, viewer, and inactive rows. newuser is not persisted."""
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        await session.execute(
            text("TRUNCATE TABLE subscriptions, users RESTART IDENTITY CASCADE")
        )
        admin = User(
            id=uuid4(),
            email=LIVE_ADMIN_EMAIL,
            password_hash=_cached_hash(LIVE_ADMIN_PASSWORD),
            role=UserRole.SUPER_ADMIN,
            token_version=1,
            is_active=True,
        )
        regular = User(
            id=uuid4(),
            email=LIVE_USER_EMAIL,
            password_hash=_cached_hash(LIVE_USER_PASSWORD),
            role=UserRole.USER,
            token_version=1,
            is_active=True,
        )
        viewer = User(
            id=uuid4(),
            email=LIVE_VIEWER_EMAIL,
            password_hash=_cached_hash(LIVE_VIEWER_PASSWORD),
            role=UserRole.VIEWER,
            token_version=1,
            is_active=True,
        )
        inactive = User(
            id=uuid4(),
            email=LIVE_INACTIVE_EMAIL,
            password_hash=_cached_hash(LIVE_INACTIVE_PASSWORD),
            role=UserRole.USER,
            token_version=1,
            is_active=False,
        )
        session.add_all([admin, regular, viewer, inactive])
        await session.commit()
        for row in (admin, regular, viewer, inactive):
            await session.refresh(row)
        yield {
            "admin": admin,
            "user": regular,
            "viewer": viewer,
            "inactive": inactive,
        }


@pytest.fixture
def admin_headers(seeded_users: dict[str, User]) -> dict[str, str]:
    """Bearer access token for the seeded Super Admin."""
    user = seeded_users["admin"]
    token = create_access_token(user.id, user.token_version)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_headers(seeded_users: dict[str, User]) -> dict[str, str]:
    """Bearer access token for the seeded regular user."""
    user = seeded_users["user"]
    token = create_access_token(user.id, user.token_version)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def viewer_headers(seeded_users: dict[str, User]) -> dict[str, str]:
    """Bearer access token for the seeded viewer."""
    user = seeded_users["viewer"]
    token = create_access_token(user.id, user.token_version)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def inactive_headers(seeded_users: dict[str, User]) -> dict[str, str]:
    """Bearer access token for the deactivated user (token still well-formed)."""
    user = seeded_users["inactive"]
    token = create_access_token(user.id, user.token_version)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def db_client(seeded_users: dict[str, User]) -> AsyncIterator[AsyncClient]:
    """HTTP client using the real test database. SES/Auth0/boto3 are mocked."""
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_auth_service, None)
    with patch(
        "app.services.email_service.EmailService.send_email",
        return_value="ses-mock-message-id",
    ), patch(
        "app.clients.ses_client.SESClient.send_email",
        return_value="ses-mock-message-id",
    ), patch(
        "boto3.client",
        return_value=MagicMock(
            send_email=MagicMock(return_value={"MessageId": "ses-mock-message-id"})
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def missing_auth_headers() -> dict[str, str]:
    """Empty headers for unauthenticated request tests."""
    return {}


@pytest.fixture
def invalid_token_headers() -> dict[str, str]:
    """Malformed bearer token for auth rejection tests."""
    return {"Authorization": "Bearer not-a-valid-jwt"}


@pytest.fixture
def stale_token_headers(seeded_users: dict[str, User]) -> dict[str, str]:
    """Access token with an outdated token_version."""
    user = seeded_users["user"]
    token = create_access_token(user.id, token_version=user.token_version + 99)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def new_user_registration_payload() -> dict[str, str]:
    """Payload for a user not yet persisted (JAW-9460 registration flow)."""
    return {
        "first_name": "New",
        "last_name": "User",
        "email": LIVE_NEW_EMAIL,
        "password": LIVE_NEW_PASSWORD,
        "role": "Coach",
    }
