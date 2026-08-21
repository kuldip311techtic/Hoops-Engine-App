"""ASGI entrypoint for Hoops Engine Apps."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import JSONResponse

from app.api.v1.endpoints import auth as auth_endpoints
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
            "Backend API for the Hoops Engine basketball training platform "
            "(Coach, Player, Organization Admin, Super Admin).\n\n"
            "Authentication is OAuth2 password flow issuing JWTs "
            "(`POST /api/v1/auth/login`, alias `POST /api/auth/login`). "
            "Public routes (login, register, refresh, health, webhooks) do not "
            "require a Bearer token. `POST /api/v1/auth/change-password` requires "
            "`Authorization: Bearer <access_token>`.\n\n"
            "All responses use a success/error envelope. Errors include "
            "`success`, `message`, `description`, and `error.code` "
            "(for example INVALID_CREDENTIALS, VALIDATION_ERROR, EMAIL_ALREADY_EXISTS). "
            "Passwords are never echoed. Successful login is HTTP 200 JSON with "
            "`data.redirect_to`; this API never issues HTTP 302."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        openapi_tags=[
            {
                "name": "auth",
                "description": (
                    "Super Admin login, registration, token refresh, and password change."
                ),
            },
            {
                "name": "health",
                "description": "Liveness and PostgreSQL readiness probes.",
            },
            {
                "name": "webhooks",
                "description": "HMAC-signed Auth0 and billing callbacks. No Bearer token.",
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
    application.include_router(auth_endpoints.router, prefix="/api/auth", tags=["auth"])
    return application


async def _rate_limit_handler(request, exc):
    """Return a 429 envelope when slowapi blocks a client."""
    return JSONResponse(
        status_code=429,
        content=error_body("Too many requests", "RATE_LIMITED", None),
    )


app = create_app()
