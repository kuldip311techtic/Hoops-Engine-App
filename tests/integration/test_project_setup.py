"""Integration tests for JAW-9448 project setup acceptance criteria."""

from pathlib import Path

from app.core.config import Settings
from app.core.security import create_access_token, decode_access_token
from app.exceptions import AppError, UnauthorizedError
from app.middleware.auth import is_public_path, refresh_access_token

ROOT = Path(__file__).resolve().parents[2]


async def test_app_package_tree_matches_scaffold() -> None:
    """JAW-9448: standard FastAPI modular-monolith folders exist."""
    required = [
        ROOT / "app" / "main.py",
        ROOT / "app" / "api" / "v1" / "router.py",
        ROOT / "app" / "api" / "v1" / "endpoints" / "health.py",
        ROOT / "app" / "core" / "config.py",
        ROOT / "app" / "core" / "security.py",
        ROOT / "app" / "core" / "logging.py",
        ROOT / "app" / "db" / "session.py",
        ROOT / "app" / "db" / "base.py",
        ROOT / "app" / "db" / "migrations" / "env.py",
        ROOT / "app" / "models",
        ROOT / "app" / "schemas",
        ROOT / "app" / "services",
        ROOT / "app" / "repositories",
        ROOT / "app" / "middleware" / "auth.py",
        ROOT / "app" / "middleware" / "cors.py",
        ROOT / "app" / "middleware" / "logging.py",
        ROOT / "app" / "middleware" / "rate_limiter.py",
        ROOT / "app" / "dependencies",
        ROOT / "app" / "exceptions",
        ROOT / "tests" / "unit" / "test_example.py",
        ROOT / "tests" / "integration" / "test_integration.py",
        ROOT / "scripts",
        ROOT / "pyproject.toml",
        ROOT / "alembic.ini",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    assert missing == []


async def test_config_exposes_asyncpg_database_urls(settings) -> None:
    """JAW-9448: DATABASE_URL and TEST_DATABASE_URL use asyncpg."""
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert settings.test_database_url.startswith("postgresql+asyncpg://")
    constructed = Settings(
        database_url="postgresql+asyncpg://user:password@localhost/dbname",
        test_database_url="postgresql+asyncpg://user:password@localhost/test_dbname",
        secret_key="s",
        jwt_secret_key="k",
    )
    assert "asyncpg" in constructed.database_url


async def test_alembic_migrations_are_initialized() -> None:
    """JAW-9448: Alembic is initialized with an initial revision chain."""
    versions = ROOT / "app" / "db" / "migrations" / "versions"
    assert (ROOT / "alembic.ini").is_file()
    assert (ROOT / "app" / "db" / "migrations" / "env.py").is_file()
    revision_files = list(versions.glob("*.py"))
    assert any("0001" in path.name for path in revision_files)
    ini = (ROOT / "alembic.ini").read_text(encoding="utf-8")
    assert "script_location = app/db/migrations" in ini


async def test_auth_skeleton_jwt_and_refresh_flow() -> None:
    """JAW-9448: JWT helpers and middleware refresh flow exist."""
    token = create_access_token("admin-id", extra_claims={"role": "super_admin"})
    payload = decode_access_token(token)
    assert payload["sub"] == "admin-id"
    assert payload["type"] == "access"
    from app.core.security import create_refresh_token

    refresh = create_refresh_token("admin-id", extra_claims={"role": "super_admin"})
    access = refresh_access_token(refresh)
    assert decode_access_token(access)["sub"] == "admin-id"
    assert is_public_path("/api/v1/auth/login") is True
    assert is_public_path("/api/v1/auth/change-password") is False


async def test_env_example_contains_required_keys() -> None:
    """JAW-9448: .env.example documents DATABASE_URL, JWT, and expiry."""
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "DATABASE_URL=" in text
    assert "JWT_SECRET" in text
    assert "ACCESS_TOKEN_EXPIRE_MINUTES=" in text
    assert "TEST_DATABASE_URL=" in text


async def test_exception_classes_and_handler_registered(app) -> None:
    """JAW-9448: custom HTTP errors and a global 500 handler are registered."""
    assert issubclass(UnauthorizedError, AppError)
    assert Exception in app.exception_handlers
    from fastapi.exceptions import RequestValidationError

    assert RequestValidationError in app.exception_handlers


async def test_logging_middleware_and_file_sink() -> None:
    """JAW-9448: loguru file sink and request logging middleware exist."""
    logging_mod = (ROOT / "app" / "core" / "logging.py").read_text(encoding="utf-8")
    assert "logger.add" in logging_mod
    assert "logs" in logging_mod
    mw = (ROOT / "app" / "middleware" / "logging.py").read_text(encoding="utf-8")
    assert "RequestLoggingMiddleware" in mw
    main = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert "RequestLoggingMiddleware" in main


async def test_cors_and_rate_limiter_wired(app, settings) -> None:
    """JAW-9448: CORS origins come from settings; slowapi is installed."""
    assert settings.cors_origin_list
    assert "*" not in settings.cors_origin_list
    assert app.state.limiter is not None
    cors_src = (ROOT / "app" / "middleware" / "cors.py").read_text(encoding="utf-8")
    assert "CORSMiddleware" in cors_src
    limiter_src = (ROOT / "app" / "middleware" / "rate_limiter.py").read_text(
        encoding="utf-8"
    )
    assert "Limiter" in limiter_src


async def test_health_endpoint_is_documented_in_openapi(client) -> None:
    """JAW-9448: OpenAPI documents GET /api/v1/health."""
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert "/api/v1/health" in spec["paths"]
    health = spec["paths"]["/api/v1/health"]["get"]
    assert health["summary"] == "Liveness probe"


async def test_pytest_layout_and_test_database_setting(settings) -> None:
    """JAW-9448: pytest layout and TEST_DATABASE_URL are configured."""
    assert (ROOT / "tests" / "unit" / "test_example.py").is_file()
    assert (ROOT / "tests" / "integration" / "test_integration.py").is_file()
    assert settings.test_database_url.startswith("postgresql+asyncpg://")


async def test_flake8_and_precommit_hooks() -> None:
    """JAW-9448: flake8 max-line-length 88 and pre-commit flake8 hook."""
    flake8 = (ROOT / ".flake8").read_text(encoding="utf-8")
    assert "max-line-length = 88" in flake8
    precommit = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    assert "flake8" in precommit
