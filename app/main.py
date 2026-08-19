"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.api.v1.router import api_router
from app.api.v1.endpoints.auth import legacy_router
from app.core.config import get_settings
from app.core.logging import logger, setup_logging
from app.exceptions.handlers import register_exception_handlers
from app.middleware.cors import setup_cors
from app.middleware.logging import LoggingMiddleware
from app.middleware.rate_limiter import setup_rate_limiter


def _custom_openapi(app: FastAPI) -> dict:
    """Generate OpenAPI schema with JWT Bearer security scheme documentation."""
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})
    openapi_schema["components"]["securitySchemes"]["HTTPBearer"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": (
            "JWT access token obtained from POST /api/login or POST /api/v1/auth/login. "
            "Include as: Authorization: Bearer <token>"
        ),
    }
    openapi_schema.setdefault("tags", [
        {"name": "health", "description": "Service health and uptime probes."},
        {"name": "auth", "description": "Super Admin authentication endpoints."},
    ])
    app.openapi_schema = openapi_schema
    return app.openapi_schema


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application startup and shutdown lifecycle hooks."""
    setup_logging()
    settings = get_settings()
    logger.info("Starting Hoops Engine API ({})", settings.environment)
    yield
    logger.info("Shutting down Hoops Engine API")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Hoops Engine API",
        description=(
            "Backend API for the Hoops Engine application. "
            "Provides authentication, training management, and admin capabilities. "
            "Public endpoints (health, login) require no auth. Protected endpoints "
            "require Authorization: Bearer <JWT> from the login response data.token field."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    setup_cors(app)
    app.add_middleware(LoggingMiddleware)
    setup_rate_limiter(app)
    register_exception_handlers(app)

    app.include_router(api_router, prefix="/api/v1")
    app.include_router(legacy_router, prefix="/api")

    app.openapi = lambda: _custom_openapi(app)

    return app


app = create_app()
