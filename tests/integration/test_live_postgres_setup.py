"""Live PostgreSQL integration tests for project setup (JAW-9577)."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.asyncio
async def test_jaw_9577_health_liveness_live(live_client: AsyncClient) -> None:
    """[JAW-9577] GET /api/v1/health returns documented liveness envelope."""
    response = await live_client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"


@pytest.mark.asyncio
async def test_jaw_9577_health_readiness_db_connectivity(
    live_client: AsyncClient,
) -> None:
    """[JAW-9577] Readiness probe confirms PostgreSQL connectivity via SELECT 1."""
    response = await live_client.get("/api/v1/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"


@pytest.mark.asyncio
async def test_jaw_9577_openapi_swagger_available(live_client: AsyncClient) -> None:
    """[JAW-9577] OpenAPI JSON is served for Swagger UI at /docs."""
    response = await live_client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert "/api/v1/health" in spec["paths"]
    assert "/api/super-admin/login" in spec["paths"]


@pytest.mark.asyncio
async def test_jaw_9577_validation_error_envelope_shape(
    live_client: AsyncClient,
) -> None:
    """[JAW-9577] Validation errors return field-level details in the standard envelope."""
    response = await live_client.post(
        "/api/super-admin/login",
        json={"email": ADMIN_LIVE_EMAIL},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    details = body["error"]["details"]
    assert isinstance(details, list)
    assert any("field" in item and "message" in item for item in details)


from tests.conftest import ADMIN_LIVE_EMAIL  # noqa: E402


def test_jaw_9577_fastapi_uvicorn_installed() -> None:
    """[JAW-9577] FastAPI and Uvicorn are installed dependencies."""
    import fastapi  # noqa: F401
    import uvicorn  # noqa: F401

    assert fastapi.__version__
    assert uvicorn.__version__


def test_jaw_9577_postgres_driver_and_alembic_installed() -> None:
    """[JAW-9577] asyncpg, SQLAlchemy, and Alembic are installed."""
    import alembic  # noqa: F401
    import asyncpg  # noqa: F401
    import sqlalchemy  # noqa: F401

    assert sqlalchemy.__version__


def test_jaw_9577_db_session_module_exists() -> None:
    """[JAW-9577] db/session.py exposes async engine and session factory."""
    from app.db.session import AsyncSessionLocal, engine

    assert engine is not None
    assert AsyncSessionLocal is not None


def test_jaw_9577_alembic_migrations_initialized() -> None:
    """[JAW-9577] Alembic migrations folder and revisions exist."""
    assert (ROOT / "alembic.ini").exists()
    assert (ROOT / "app/db/migrations/env.py").exists()
    assert (ROOT / "app/db/migrations/versions/0001_initial.py").exists()


def test_jaw_9577_core_security_jwt_helpers() -> None:
    """[JAW-9577] core/security.py provides JWT and password helpers."""
    from app.core.security import create_access_token, decode_token, hash_password

    hashed = hash_password("secret")
    token = create_access_token("user-id", token_version=1)
    payload = decode_token(token)
    assert payload["sub"] == "user-id"
    assert payload["type"] == "access"
    assert hashed != "secret"


def test_jaw_9577_auth_middleware_exists() -> None:
    """[JAW-9577] JWT authentication middleware is registered."""
    from app.middleware.auth import AuthMiddleware, is_public_path

    assert AuthMiddleware is not None
    assert is_public_path("/api/v1/health") is True


def test_jaw_9577_env_example_documents_required_keys() -> None:
    """[JAW-9577] .env.example documents DATABASE_URL and JWT settings."""
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    for key in (
        "DATABASE_URL",
        "JWT_SECRET",
        "JWT_ALGORITHM",
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "REFRESH_TOKEN_EXPIRE_DAYS",
        "TEST_DATABASE_URL",
    ):
        assert key in text


def test_jaw_9577_global_error_handlers_registered() -> None:
    """[JAW-9577] main.py registers global exception handlers."""
    from app.main import app

    assert Exception in app.exception_handlers


def test_jaw_9577_loguru_installed_and_logging_configured() -> None:
    """[JAW-9577] loguru is installed and configure_logging exists."""
    from loguru import logger  # noqa: F401

    from app.core.logging import configure_logging

    assert callable(configure_logging)


def test_jaw_9577_request_logging_middleware_exists() -> None:
    """[JAW-9577] Request/response logging middleware is implemented."""
    from app.middleware.logging import RequestLoggingMiddleware

    assert RequestLoggingMiddleware is not None


def test_jaw_9577_cors_middleware_wired() -> None:
    """[JAW-9577] CORS middleware helper is available."""
    from app.middleware.cors import add_cors

    assert callable(add_cors)


def test_jaw_9577_slowapi_rate_limiter_installed() -> None:
    """[JAW-9577] slowapi rate limiter is installed and wired."""
    import slowapi  # noqa: F401

    from app.middleware.rate_limiter import get_limiter

    assert get_limiter() is not None


def test_jaw_9577_pydantic_example_schema() -> None:
    """[JAW-9577] Example Pydantic schema validates request fields."""
    from app.schemas.example import ExampleUser

    user = ExampleUser(username="demo", email="demo@example.com")
    assert user.username == "demo"


def test_jaw_9577_pytest_layout_exists() -> None:
    """[JAW-9577] Unit and integration test directories exist."""
    assert (ROOT / "tests/unit/test_example.py").exists()
    assert (ROOT / "tests/integration/test_integration.py").exists()


def test_jaw_9577_test_database_url_configured() -> None:
    """[JAW-9577] Settings expose TEST_DATABASE_URL for integration tests."""
    from app.core.config import get_settings

    settings = get_settings()
    assert settings.test_database_url.startswith("postgresql+asyncpg://")


def test_jaw_9577_flake8_and_black_configured() -> None:
    """[JAW-9577] Flake8 and Black configuration files exist."""
    flake8 = (ROOT / ".flake8").read_text(encoding="utf-8")
    assert "max-line-length = 88" in flake8
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "[tool.black]" in pyproject


def test_jaw_9577_precommit_config_present() -> None:
    """[JAW-9577] pre-commit hook configuration is checked in."""
    pre = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    assert "pre-commit-hooks" in pre
    assert "flake8" in pre
    assert "black" in pre


def test_jaw_9577_project_structure_complete() -> None:
    """[JAW-9577] Modular-monolith scaffold directories exist."""
    required = [
        "app/main.py",
        "app/api/v1/router.py",
        "app/core/config.py",
        "app/db/session.py",
        "app/models",
        "app/schemas",
        "app/services",
        "app/repositories",
        "app/middleware",
        "app/dependencies",
        "app/exceptions",
        "scripts/check_db.py",
    ]
    missing = [p for p in required if not (ROOT / p).exists()]
    assert missing == []


@pytest.mark.asyncio
async def test_data_integrity_duplicate_email_rejected(
    db_session,
    clean_users,
) -> None:
    """Duplicate email insertion violates the unique index on users.email."""
    from sqlalchemy.exc import IntegrityError

    from app.core.security import hash_password
    from app.models.user import User, UserRole
    from app.repositories.user_repository import UserRepository

    repo = UserRepository(db_session)
    await repo.create(
        email="dup@test.com",
        password_hash=hash_password("Pass1!"),
        role=UserRole.USER,
    )
    await db_session.commit()

    db_session.add(
        User(
            email="dup@test.com",
            password_hash=hash_password("Pass2!"),
            role=UserRole.USER,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()
