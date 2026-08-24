"""Shared pytest fixtures for in-memory and live PostgreSQL integration tests."""

from __future__ import annotations

import os
import secrets
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

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

from alembic import command
from alembic.config import Config

from app.core.config import get_settings

get_settings.cache_clear()

from app.core.security import (
    create_access_token,
    hash_password,
)
from app.dependencies.auth import get_auth_service
from app.dependencies.db import get_db
from app.main import app
from app.models.support_request import SupportRequestStatus
from app.models.user import User, UserRole
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.support_request_repository import SupportRequestRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from tests.fakes import InMemoryUserRepository

# In-memory login fixture credentials (existing fast tests)
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD") or f"Aa1!{secrets.token_hex(8)}"

# Live PostgreSQL seed credentials (five test users)
ADMIN_LIVE_EMAIL = "admin@test.com"
ADMIN_LIVE_PASSWORD = os.environ.get("TEST_LIVE_ADMIN_PASSWORD") or f"Aa1!{secrets.token_hex(8)}"
USER_LIVE_EMAIL = "user@test.com"
USER_LIVE_PASSWORD = os.environ.get("TEST_LIVE_USER_PASSWORD") or f"Aa1!{secrets.token_hex(8)}"
VIEWER_LIVE_EMAIL = "viewer@test.com"
VIEWER_LIVE_PASSWORD = os.environ.get("TEST_LIVE_VIEWER_PASSWORD") or f"Aa1!{secrets.token_hex(8)}"
INACTIVE_LIVE_EMAIL = "inactive@test.com"
INACTIVE_LIVE_PASSWORD = os.environ.get("TEST_LIVE_INACTIVE_PASSWORD") or f"Aa1!{secrets.token_hex(8)}"
NEW_USER_EMAIL = "newuser@test.com"
NEW_USER_PASSWORD = os.environ.get("TEST_LIVE_NEW_USER_PASSWORD") or f"Aa1!{secrets.token_hex(8)}"

SAMPLE_USERS: tuple[dict[str, object], ...] = (
    {
        "key": "admin",
        "email": ADMIN_LIVE_EMAIL,
        "password": ADMIN_LIVE_PASSWORD,
        "role": UserRole.SUPER_ADMIN,
        "is_active": True,
    },
    {
        "key": "user",
        "email": USER_LIVE_EMAIL,
        "password": USER_LIVE_PASSWORD,
        "role": UserRole.USER,
        "is_active": True,
    },
    {
        "key": "viewer",
        "email": VIEWER_LIVE_EMAIL,
        "password": VIEWER_LIVE_PASSWORD,
        "role": UserRole.VIEWER,
        "is_active": True,
    },
    {
        "key": "inactive",
        "email": INACTIVE_LIVE_EMAIL,
        "password": INACTIVE_LIVE_PASSWORD,
        "role": UserRole.SUPER_ADMIN,
        "is_active": False,
    },
    {
        "key": "new",
        "email": NEW_USER_EMAIL,
        "password": NEW_USER_PASSWORD,
        "skip_insert": True,
    },
)


async def _fake_db() -> AsyncIterator[MagicMock]:
    """Yield a session mock so HTTP tests never require live Postgres."""
    session = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock())
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    yield session


@pytest.fixture(scope="session")
def migrated_db() -> Iterator[None]:
    """Apply Alembic migrations once against TEST_DATABASE_URL."""
    cfg = Config(str(ROOT / "alembic.ini"))
    command.upgrade(cfg, "head")
    yield


@pytest.fixture
async def db_session(migrated_db: None) -> AsyncIterator[AsyncSession]:
    """Yield a real async SQLAlchemy session bound to the test database."""
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def clean_users(db_session: AsyncSession) -> AsyncIterator[None]:
    """Truncate user-related tables before and after each live DB test."""
    await db_session.rollback()
    await db_session.execute(
        text("TRUNCATE TABLE subscriptions, users RESTART IDENTITY CASCADE")
    )
    await db_session.commit()
    yield
    await db_session.rollback()
    await db_session.execute(
        text("TRUNCATE TABLE subscriptions, users RESTART IDENTITY CASCADE")
    )
    await db_session.commit()


@pytest.fixture
async def clean_organizations(db_session: AsyncSession) -> AsyncIterator[None]:
    """Truncate organizations before and after each live DB test."""
    await db_session.rollback()
    await db_session.execute(text("TRUNCATE TABLE organizations RESTART IDENTITY"))
    await db_session.commit()
    yield
    await db_session.rollback()
    await db_session.execute(text("TRUNCATE TABLE organizations RESTART IDENTITY"))
    await db_session.commit()


@pytest.fixture
async def seed_organization(
    clean_organizations: None,
    db_session: AsyncSession,
) -> dict[str, object]:
    """Insert sample organizations for integration tests."""
    repo = OrganizationRepository(db_session)
    active = await repo.create(
        name="Organization Name",
        contact_email="contact@example.com",
        phone_number="1234567890",
        address="123 Main St",
    )
    inactive = await repo.create(
        name="Removed Org",
        contact_email="removed@example.com",
        phone_number="5555555555",
        address="999 Closed Rd",
    )
    inactive = await repo.deactivate(inactive)
    await db_session.commit()
    return {"active": active, "inactive": inactive}


@pytest.fixture
async def clean_support_requests(db_session: AsyncSession) -> AsyncIterator[None]:
    """Truncate support_requests before and after each live DB test."""
    await db_session.rollback()
    await db_session.execute(text("TRUNCATE TABLE support_requests RESTART IDENTITY"))
    await db_session.commit()
    yield
    await db_session.rollback()
    await db_session.execute(text("TRUNCATE TABLE support_requests RESTART IDENTITY"))
    await db_session.commit()


@pytest.fixture
async def seed_five_users(
    clean_users: None,
    db_session: AsyncSession,
) -> dict[str, User]:
    """Insert four users into PostgreSQL; fifth (newuser) remains unregistered."""
    repo = UserRepository(db_session)
    seeded: dict[str, User] = {}
    for spec in SAMPLE_USERS:
        if spec.get("skip_insert"):
            continue
        user = await repo.create(
            email=str(spec["email"]),
            password_hash=hash_password(str(spec["password"])),
            role=spec["role"],  # type: ignore[arg-type]
        )
        user.is_active = bool(spec["is_active"])
        await db_session.flush()
        seeded[str(spec["key"])] = user
    await db_session.commit()
    return seeded


@pytest.fixture
async def seed_support_request(
    clean_support_requests: None,
    seed_five_users: dict[str, User],
    db_session: AsyncSession,
) -> dict[str, object]:
    """Insert sample support requests for integration tests."""
    repo = SupportRequestRepository(db_session)
    submitter = seed_five_users["user"]
    open_request = await repo.create(
        subject="Cannot access practice plans",
        message="I am unable to view practice plans after logging in.",
        submitter_user_id=submitter.id,
    )
    closed_request = await repo.create(
        subject="Billing question",
        message="How do I update my subscription?",
        submitter_user_id=submitter.id,
        status=SupportRequestStatus.CLOSED,
    )
    closed_request.closed_at = datetime.now(UTC)
    await db_session.commit()
    return {"open": open_request, "closed": closed_request}


@pytest.fixture
async def live_client(migrated_db: None) -> AsyncIterator[AsyncClient]:
    """HTTP client using real PostgreSQL via dependency injection (no overrides)."""
    app.dependency_overrides.clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def admin_access_token(seed_five_users: dict[str, User]) -> str:
    """Bearer access token for the seeded Super Admin user."""
    admin = seed_five_users["admin"]
    return create_access_token(admin.id, admin.token_version)


@pytest.fixture
def user_access_token(seed_five_users: dict[str, User]) -> str:
    """Bearer access token for the seeded regular user."""
    user = seed_five_users["user"]
    return create_access_token(user.id, user.token_version)


@pytest.fixture
def viewer_access_token(seed_five_users: dict[str, User]) -> str:
    """Bearer access token for the seeded viewer user."""
    viewer = seed_five_users["viewer"]
    return create_access_token(viewer.id, viewer.token_version)




@pytest.fixture
def inactive_access_token(seed_five_users: dict[str, User]) -> str:
    """Bearer access token for the seeded inactive Super Admin user."""
    inactive = seed_five_users["inactive"]
    return create_access_token(inactive.id, inactive.token_version)

@pytest.fixture
def expired_access_token(seed_five_users: dict[str, User]) -> str:
    """Expired JWT for auth rejection tests."""
    from jose import jwt

    admin = seed_five_users["admin"]
    settings = get_settings()
    expired = datetime.now(UTC) - timedelta(minutes=5)
    claims = {
        "sub": str(admin.id),
        "type": "access",
        "ver": admin.token_version,
        "exp": expired,
    }
    return jwt.encode(
        claims,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


# --- Existing in-memory fixtures (backward compatible) ---


@pytest.fixture
def users() -> InMemoryUserRepository:
    """Empty in-memory user repository."""
    return InMemoryUserRepository()


@pytest.fixture
def admin_user(users: InMemoryUserRepository) -> User:
    """Seed a Super Admin used by in-memory login tests."""
    user = User(
        email=ADMIN_EMAIL,
        first_name="Admin",
        last_name="User",
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
