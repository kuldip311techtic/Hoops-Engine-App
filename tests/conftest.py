"""Shared pytest fixtures."""

import os

import pytest
from httpx import ASGITransport, AsyncClient

# Ensure required settings exist before importing the application.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:password@localhost:5432/hoopsengine_test",
)
os.environ.setdefault(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:password@localhost:5432/hoopsengine_test",
)
os.environ.setdefault("SECRET_KEY", "test-secret-key-min-16-chars")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-min-32-chars!!")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("LOG_LEVEL", "WARNING")

from app.core.config import get_settings
from app.main import create_app

get_settings.cache_clear()


@pytest.fixture
async def client() -> AsyncClient:
    """Provide an async HTTP client bound to the FastAPI app."""
    application = create_app()
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
