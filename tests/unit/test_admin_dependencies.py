"""Unit tests for Super Admin authorization dependencies."""

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.dependencies.admin import get_current_super_admin
from app.dependencies.auth import get_current_user
from app.exceptions.handlers import register_exception_handlers
from app.models.user import User, UserRole


def _build_app() -> FastAPI:
    """Build a tiny app that exposes the super-admin guard."""
    application = FastAPI()
    register_exception_handlers(application)

    @application.get("/protected")
    async def protected(admin: User = Depends(get_current_super_admin)) -> dict:
        """Return the authenticated admin email."""
        return {"email": admin.email}

    return application


@pytest.mark.asyncio
async def test_get_current_super_admin_allows_admin_role(admin_user: User) -> None:
    """Super Admin role passes the guard."""
    app = _build_app()

    async def _override_user() -> User:
        return admin_user

    app.dependency_overrides[get_current_user] = _override_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/protected")
    assert response.status_code == 200
    assert response.json()["email"] == admin_user.email


@pytest.mark.asyncio
async def test_get_current_super_admin_rejects_user_role() -> None:
    """Regular USER role returns 403 FORBIDDEN."""
    user = User(
        email="user@test.com",
        password_hash="hash",
        role=UserRole.USER,
        token_version=1,
        is_active=True,
    )
    app = _build_app()

    async def _override_user() -> User:
        return user

    app.dependency_overrides[get_current_user] = _override_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/protected")
    assert response.status_code == 403
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_get_current_super_admin_rejects_viewer_role() -> None:
    """VIEWER role returns 403 FORBIDDEN."""
    viewer = User(
        email="viewer@test.com",
        password_hash="hash",
        role=UserRole.VIEWER,
        token_version=1,
        is_active=True,
    )
    app = _build_app()

    async def _override_user() -> User:
        return viewer

    app.dependency_overrides[get_current_user] = _override_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/protected")
    assert response.status_code == 403
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "FORBIDDEN"
