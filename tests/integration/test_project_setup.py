"""Scaffold / project-setup structural tests."""

from pathlib import Path

import pytest
from httpx import AsyncClient

ROOT = Path(__file__).resolve().parents[2]


def test_app_package_tree_matches_scaffold() -> None:
    """Required modular-monolith paths exist."""
    required = [
        "pyproject.toml",
        "requirements.txt",
        ".env.example",
        "app/main.py",
        "app/api/v1/router.py",
        "app/api/v1/endpoints/health.py",
        "app/core/config.py",
        "app/core/security.py",
        "app/core/logging.py",
        "app/db/session.py",
        "app/db/base.py",
        "app/db/migrations/env.py",
        "app/models",
        "app/schemas",
        "app/services",
        "app/repositories",
        "app/middleware/auth.py",
        "app/middleware/cors.py",
        "app/middleware/logging.py",
        "app/middleware/rate_limiter.py",
        "app/dependencies",
        "app/exceptions/base.py",
        "tests/unit/test_example.py",
        "tests/integration/test_integration.py",
        "scripts/check_db.py",
    ]
    missing = [path for path in required if not (ROOT / path).exists()]
    assert missing == []


def test_config_exposes_asyncpg_database_urls() -> None:
    """Settings expose asyncpg URLs."""
    from app.core.config import get_settings

    settings = get_settings()
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert settings.test_database_url.startswith("postgresql+asyncpg://")


def test_alembic_migrations_are_initialized() -> None:
    """Alembic is initialized under app/db/migrations with an initial revision."""
    ini = (ROOT / "alembic.ini").read_text()
    assert "app/db/migrations" in ini
    assert (ROOT / "app/db/migrations/versions/0001_initial.py").exists()
    assert (ROOT / "app/db/migrations/versions/0002_auth_tables.py").exists()


def test_auth_skeleton_jwt_and_refresh_flow() -> None:
    """JWT helpers and refresh_access_token are importable."""
    from app.core import security
    from app.middleware.auth import refresh_access_token

    token = security.create_refresh_token("sub")
    access = refresh_access_token(token)
    assert security.decode_token(access)["type"] == "access"


def test_exception_classes_and_handler_registered() -> None:
    """Custom exceptions exist and the app has a catch-all handler."""
    from app.exceptions import AppError, UnauthorizedError
    from app.main import app

    assert issubclass(UnauthorizedError, AppError)
    assert Exception in app.exception_handlers


def test_env_example_contains_required_keys() -> None:
    """`.env.example` documents DATABASE_URL, JWT_SECRET, ACCESS_TOKEN_EXPIRE_MINUTES."""
    text = (ROOT / ".env.example").read_text()
    for key in (
        "DATABASE_URL",
        "JWT_SECRET",
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "TEST_DATABASE_URL",
    ):
        assert key in text


def test_cors_and_rate_limiter_wired() -> None:
    """CORS helper and limiter exist."""
    from app.middleware.cors import add_cors
    from app.middleware.rate_limiter import get_limiter

    assert callable(add_cors)
    assert get_limiter() is not None


@pytest.mark.asyncio
async def test_health_endpoint_is_documented_in_openapi(client: AsyncClient) -> None:
    """Health appears in OpenAPI with a summary."""
    spec = (await client.get("/openapi.json")).json()
    health = spec["paths"]["/api/v1/health"]["get"]
    assert health.get("summary")
    assert "health" in health.get("tags", [])


def test_logging_middleware_and_file_sink() -> None:
    """Logging middleware and configure_logging exist."""
    from app.core.logging import configure_logging
    from app.middleware.logging import RequestLoggingMiddleware

    assert callable(configure_logging)
    assert RequestLoggingMiddleware is not None


def test_pytest_layout_and_test_database_setting() -> None:
    """Unit/integration layout and TEST_DATABASE_URL are present."""
    assert (ROOT / "tests/unit/test_example.py").exists()
    assert (ROOT / "tests/integration/test_integration.py").exists()
    from app.core.config import get_settings

    assert get_settings().test_database_url


def test_flake8_and_precommit_hooks() -> None:
    """flake8 config and pre-commit hooks are checked in."""
    flake8 = (ROOT / ".flake8").read_text()
    assert "max-line-length = 88" in flake8
    pre = (ROOT / ".pre-commit-config.yaml").read_text()
    assert "flake8" in pre
