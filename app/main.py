"""ASGI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.endpoints import auth as auth_endpoints
from app.api.v1.router import api_router
from app.core.logging import configure_logging
from app.db.session import dispose_engine
from app.exceptions.handlers import register_exception_handlers
from app.middleware.auth import AuthMiddleware
from app.middleware.cors import add_cors_middleware
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.rate_limiter import limiter, rate_limit_exceeded_handler


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Configure logging on startup and dispose the DB engine on shutdown."""
    configure_logging()
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    configure_logging()
    app = FastAPI(
        title="Hoops Engine Apps",
        description=(
            "Backend API for Hoops Engine. All successful responses use "
            "``{success, message, data}``. Errors use "
            "``{success, message, error: {code, details}}``."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=[
            {
                "name": "health",
                "description": "Liveness and readiness probes. Public, no auth.",
            },
            {
                "name": "auth",
                "description": (
                    "Super Admin OAuth2 login, session refresh, and password change. "
                    "Login and refresh are public; change-password requires a Bearer token."
                ),
            },
            {
                "name": "webhooks",
                "description": "Auth0 and billing provider callbacks. HMAC signature required.",
            },
        ],
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    register_exception_handlers(app)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(AuthMiddleware)
    app.add_middleware(SlowAPIMiddleware)
    add_cors_middleware(app)
    app.include_router(api_router, prefix="/api/v1")
    # Frontend contract: POST /api/auth/login (same handler as /api/v1/auth/login)
    app.include_router(auth_endpoints.router, prefix="/api")
    return app


app = create_app()
