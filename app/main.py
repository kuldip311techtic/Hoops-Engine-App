"""ASGI entrypoint for Hoops Engine Apps."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import JSONResponse

from app.api.v1.endpoints import super_admin
from app.api.v1.router import api_router
from app.core.logging import configure_logging
from app.db.session import engine
from app.exceptions.handlers import register_exception_handlers
from app.middleware.auth import AuthMiddleware
from app.middleware.cors import add_cors
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.rate_limiter import limiter
from app.schemas.common import error_body


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Dispose the SQLAlchemy engine on shutdown."""
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    configure_logging()
    application = FastAPI(
        title="Hoops Engine Apps",
        version="0.1.0",
        description=(
            "Backend API for the Hoops Engine basketball training platform.\n\n"
            "All responses use a success/error envelope. Errors include "
            "`success`, `message`, `description`, and `error.code` "
            "(for example VALIDATION_ERROR, UNAUTHORIZED, INTERNAL_ERROR). "
            "Field-level validation details appear under `error.details`.\n\n"
            "Public routes (health, Super Admin login) require no Authorization "
            "header. Protected routes expect `Authorization: Bearer <access_token>`."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        openapi_tags=[
            {
                "name": "health",
                "description": "Liveness and PostgreSQL readiness probes.",
            },
            {
                "name": "super-admin",
                "description": "Super Admin authentication for the dashboard login screen.",
            },
        ],
    )
    register_exception_handlers(application)
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
    application.add_middleware(RequestLoggingMiddleware)
    application.add_middleware(AuthMiddleware)
    add_cors(application)
    application.add_middleware(SlowAPIMiddleware)
    application.include_router(api_router, prefix="/api/v1")
    application.include_router(
        super_admin.router,
        prefix="/api/super-admin",
        tags=["super-admin"],
    )

    def custom_openapi() -> dict:
        """Attach Bearer JWT security scheme for protected endpoints."""
        if application.openapi_schema:
            return application.openapi_schema
        schema = get_openapi(
            title=application.title,
            version=application.version,
            description=application.description,
            routes=application.routes,
            tags=application.openapi_tags,
        )
        schema.setdefault("components", {}).setdefault("securitySchemes", {})
        schema["components"]["securitySchemes"]["BearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "JWT access token from POST /api/super-admin/login. "
                "Public routes declare security: [] and do not require this header."
            ),
        }
        application.openapi_schema = schema
        return schema

    application.openapi = custom_openapi  # type: ignore[method-assign]
    return application


async def _rate_limit_handler(_request: Request, _exc: RateLimitExceeded) -> JSONResponse:
    """Return a 429 envelope when slowapi blocks a client."""
    return JSONResponse(
        status_code=429,
        content=error_body("Too many requests", "RATE_LIMITED", None),
    )


app = create_app()
