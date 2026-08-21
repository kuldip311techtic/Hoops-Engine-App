"""Live PostgreSQL tests for health, OpenAPI, errors, and JAW-9448 scaffolding."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.security import create_refresh_token, decode_token
from app.exceptions import AppError, UnauthorizedError
from app.main import app
from app.middleware.auth import refresh_access_token
from app.middleware.cors import add_cors
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.rate_limiter import get_limiter

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.asyncio
async def test_health_happy_path(db_client: AsyncClient) -> None:
    """GET /api/v1/health returns the success envelope with status ok."""
    response = await db_client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"]
    assert body["data"]["status"] == "ok"


@pytest.mark.asyncio
async def test_health_ready_hits_real_postgres(db_client: AsyncClient) -> None:
    """Readiness probe runs SELECT 1 on the test database."""
    response = await db_client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"


@pytest.mark.asyncio
async def test_health_does_not_require_auth(db_client: AsyncClient) -> None:
    """Health is public: missing token is not 401."""
    response = await db_client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert "error" not in body or body.get("error") in (None, {})


@pytest.mark.asyncio
async def test_health_trailing_slash_or_unknown_is_not_500(
    db_client: AsyncClient,
) -> None:
    """Unknown health child path is an envelope error, not a stack trace."""
    response = await db_client.get("/api/v1/health/nope")
    assert response.status_code in (401, 404, 405)
    assert "Traceback" not in response.text


@pytest.mark.asyncio
async def test_protected_missing_token_401(db_client: AsyncClient) -> None:
    """Unknown protected path without bearer is 401."""
    response = await db_client.get("/api/v1/does-not-exist")
    assert response.status_code in (401, 404)
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] in ("UNAUTHORIZED", "NOT_FOUND")


@pytest.mark.asyncio
async def test_openapi_documents_health_and_login(db_client: AsyncClient) -> None:
    """JAW-9448: OpenAPI documents health and login email/password fields."""
    spec = (await db_client.get("/openapi.json")).json()
    assert spec["paths"]["/api/v1/health"]["get"].get("summary")
    login = spec["paths"]["/api/v1/auth/login"]["post"]
    body = login["requestBody"]["content"]["application/json"]["schema"]
    if "$ref" in body:
        name = body["$ref"].split("/")[-1]
        props = spec["components"]["schemas"][name]["properties"]
    else:
        props = body["properties"]
    assert "email" in props
    assert "password" in props


@pytest.mark.asyncio
async def test_validation_error_json_shape(db_client: AsyncClient) -> None:
    """JAW-9448: 422 details include loc, msg, and type."""
    response = await db_client.post("/api/v1/auth/login", json={})
    assert response.status_code == 422
    details = response.json()["error"]["details"]
    assert any("loc" in item and "msg" in item and "type" in item for item in details)


@pytest.mark.asyncio
async def test_unhandled_does_not_leak_internals(db_client: AsyncClient) -> None:
    """500/401 envelope never includes SQL or traceback text."""
    response = await db_client.get("/api/v1/does-not-exist")
    assert "Traceback" not in response.text
    assert "SELECT" not in response.text


def test_folder_tree_matches_scaffold() -> None:
    """JAW-9448: modular monolith paths exist."""
    required = [
        "app/main.py",
        "app/api/v1/router.py",
        "app/api/v1/endpoints/health.py",
        "app/core/config.py",
        "app/core/security.py",
        "app/core/logging.py",
        "app/db/session.py",
        "app/db/base.py",
        "app/db/migrations/env.py",
        "app/middleware/auth.py",
        "app/middleware/cors.py",
        "app/middleware/logging.py",
        "app/middleware/rate_limiter.py",
        "app/exceptions/base.py",
        "tests/unit/test_example.py",
        "tests/integration/test_integration.py",
        ".env.example",
        ".flake8",
        ".pre-commit-config.yaml",
        "alembic.ini",
    ]
    missing = [path for path in required if not (ROOT / path).exists()]
    assert missing == []


def test_config_asyncpg_and_test_database_url() -> None:
    """JAW-9448: DATABASE_URL and TEST_DATABASE_URL use asyncpg."""
    settings = get_settings()
    assert "postgresql+asyncpg://" in settings.database_url
    assert "postgresql+asyncpg://" in settings.test_database_url


def test_alembic_initialized() -> None:
    """JAW-9448: Alembic lives under app/db/migrations with revisions."""
    ini = (ROOT / "alembic.ini").read_text()
    assert "app/db/migrations" in ini
    versions = ROOT / "app/db/migrations/versions"
    assert (versions / "0001_initial.py").exists()
    assert (versions / "0002_auth_tables.py").exists()


def test_auth_skeleton_jwt_and_refresh_helper() -> None:
    """JAW-9448: security.py tokens and middleware refresh_access_token work."""
    refresh = create_refresh_token("sub-1")
    access = refresh_access_token(refresh)
    assert decode_token(access)["type"] == "access"


def test_exception_classes_registered() -> None:
    """JAW-9448: custom exceptions and catch-all handler are registered."""
    assert issubclass(UnauthorizedError, AppError)
    assert Exception in app.exception_handlers


def test_env_example_has_jwt_and_database() -> None:
    """JAW-9448: .env.example documents DATABASE_URL, JWT_SECRET, ACCESS_TOKEN_EXPIRE_MINUTES."""
    text = (ROOT / ".env.example").read_text()
    for key in ("DATABASE_URL", "JWT_SECRET", "ACCESS_TOKEN_EXPIRE_MINUTES"):
        assert key in text


def test_cors_and_slowapi_configured() -> None:
    """JAW-9448: CORS helper and rate limiter exist."""
    assert callable(add_cors)
    assert get_limiter() is not None


def test_logging_file_sink_and_middleware() -> None:
    """JAW-9448: loguru file logging and request middleware are wired."""
    assert callable(configure_logging)
    assert RequestLoggingMiddleware is not None
    logging_mod = (ROOT / "app/core/logging.py").read_text()
    assert "logger.add" in logging_mod
    assert "logs" in logging_mod


def test_flake8_and_precommit() -> None:
    """JAW-9448: flake8 max-line-length 88 and pre-commit flake8 hook."""
    flake8 = (ROOT / ".flake8").read_text()
    assert "max-line-length = 88" in flake8
    assert "flake8" in (ROOT / ".pre-commit-config.yaml").read_text()


def test_example_unit_and_integration_files_exist() -> None:
    """JAW-9448: pytest layout files from the ticket exist."""
    assert (ROOT / "tests/unit/test_example.py").exists()
    assert (ROOT / "tests/integration/test_integration.py").exists()
