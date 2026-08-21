"""Shared pytest fixtures: PostgreSQL test DB, HTTP client, Super Admin users."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path
from urllib.parse import urlparse
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv(path: Path) -> None:
    """Load KEY=VALUE pairs without overriding existing process env."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(ROOT / ".env.test")
_load_dotenv(ROOT / ".env")

_DEFAULT_TEST_URL = (
    "postgresql+asyncpg://postgres:1234@localhost:5432/hoopsengine"
)
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or _DEFAULT_TEST_URL
os.environ["TEST_DATABASE_URL"] = TEST_DATABASE_URL
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key")
os.environ.setdefault("AUTH0_WEBHOOK_SECRET", "test-auth0-webhook-secret")
os.environ.setdefault("BILLING_WEBHOOK_SECRET", "test-billing-webhook-secret")
os.environ["ENVIRONMENT"] = "test"
os.environ.setdefault("DASHBOARD_PATH", "/dashboard")
os.environ.setdefault("LOGIN_RATE_LIMIT", "1000/minute")

from app.core.config import get_settings  # noqa: E402
from app.main import create_app  # noqa: E402

ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "TestAdmin123!"
USER_EMAIL = "user@test.com"
USER_PASSWORD = "TestUser123!"
VIEWER_EMAIL = "viewer@test.com"
VIEWER_PASSWORD = "TestViewer123!"
INACTIVE_EMAIL = "inactive@test.com"
INACTIVE_PASSWORD = "TestInactive123!"
NEW_USER_EMAIL = "newuser@test.com"
NEW_USER_PASSWORD = "NewUser123!"

SEEDED_USERS = (
    {
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
        "role": "admin",
        "token_version": 0,
    },
    {
        "email": USER_EMAIL,
        "password": USER_PASSWORD,
        "role": "user",
        "token_version": 0,
    },
    {
        "email": VIEWER_EMAIL,
        "password": VIEWER_PASSWORD,
        "role": "viewer",
        "token_version": 0,
    },
    {
        "email": INACTIVE_EMAIL,
        "password": INACTIVE_PASSWORD,
        "role": "user",
        "token_version": 1,
    },
)


def _ensure_postgres_database(async_url: str) -> None:
    """Create the test database if it does not already exist."""
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

    sync_url = async_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    parsed = urlparse(sync_url)
    dbname = (parsed.path or "").lstrip("/")
    if not dbname.replace("_", "").isalnum():
        raise RuntimeError(f"Refusing to create database {dbname!r}")
    admin = parsed._replace(path="/postgres").geturl()
    conn = psycopg2.connect(admin)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
    if cur.fetchone() is None:
        cur.execute(f'CREATE DATABASE "{dbname}"')
    cur.close()
    conn.close()


def _run_alembic_upgrade() -> None:
    """Apply Alembic migrations to the PostgreSQL test database."""
    from alembic import command
    from alembic.config import Config

    get_settings.cache_clear()
    cfg = Config(str(ROOT / "alembic.ini"))
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session", autouse=True)
def _migrated_test_database() -> None:
    """Create hoopsengine_test and migrate once per pytest session."""
    _ensure_postgres_database(TEST_DATABASE_URL)
    _run_alembic_upgrade()
    yield
    get_settings.cache_clear()


@pytest.fixture(scope="session")
def password_hashes(_migrated_test_database) -> dict[str, str]:
    """Bcrypt hashes for seeded Super Admins (computed once)."""
    from app.core.security import hash_password

    return {
        ADMIN_EMAIL: hash_password(ADMIN_PASSWORD),
        USER_EMAIL: hash_password(USER_PASSWORD),
        VIEWER_EMAIL: hash_password(VIEWER_PASSWORD),
        INACTIVE_EMAIL: hash_password(INACTIVE_PASSWORD),
    }


@pytest.fixture(autouse=True)
def mock_third_party_services():
    """Block boto3 SES HTTP; do not patch SESClient.send_email itself.

    Unit tests in test_ses_client.py exercise send_email() with a stub
    ``_client``. Patching send_email globally forced those tests to see
    ``ses-message-id-test`` and skipped EmailNotConfiguredError / EmailDeliveryError.
    """
    with patch("app.clients.ses_client.SESClient._get_boto_client") as boto:
        boto.return_value.send_email.return_value = {"MessageId": "ses-message-id-test"}
        yield


@pytest.fixture
def settings():
    """Return cached settings (cleared after the test)."""
    get_settings.cache_clear()
    try:
        yield get_settings()
    finally:
        get_settings.cache_clear()


@pytest.fixture
def app():
    """Fresh FastAPI app instance bound at the test DATABASE_URL."""
    get_settings.cache_clear()
    return create_app()


@pytest.fixture
async def seed_users(password_hashes) -> list[dict]:
    """Truncate auth tables and insert four Super Admin rows."""
    from app.db.session import get_session_factory
    from app.models.super_admin import SuperAdmin

    factory = get_session_factory()
    async with factory() as session:
        await session.execute(
            text("TRUNCATE TABLE subscriptions, super_admins RESTART IDENTITY CASCADE")
        )
        for row in SEEDED_USERS:
            session.add(
                SuperAdmin(
                    email=row["email"],
                    hashed_password=password_hashes[row["email"]],
                    token_version=row["token_version"],
                )
            )
        await session.commit()
    return list(SEEDED_USERS)


@pytest.fixture
async def db_session(seed_users):
    """Yield an AsyncSession against the migrated test database."""
    from app.db.session import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        yield session


@pytest.fixture
async def client(app, seed_users) -> AsyncIterator[AsyncClient]:
    """HTTPX async client bound to the ASGI app (real DB via Depends)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


@pytest.fixture
async def admin_login(client) -> dict:
    """POST login for admin@test.com and return the data object."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    return body["data"]


@pytest.fixture
async def admin_token(admin_login) -> str:
    """Bearer access token for the admin Super Admin."""
    return admin_login["access_token"]


@pytest.fixture
async def admin_headers(admin_token) -> dict[str, str]:
    """Authorization header for the admin Super Admin."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def new_user() -> dict:
    """Registration payload that is not inserted into the database."""
    return {"email": NEW_USER_EMAIL, "password": NEW_USER_PASSWORD, "role": "user"}
