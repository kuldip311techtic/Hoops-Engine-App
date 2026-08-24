"""Live PostgreSQL integration tests for Super Admin login (JAW-9606)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import (
    ADMIN_LIVE_EMAIL,
    ADMIN_LIVE_PASSWORD,
    INACTIVE_LIVE_EMAIL,
    INACTIVE_LIVE_PASSWORD,
    NEW_USER_EMAIL,
    NEW_USER_PASSWORD,
    USER_LIVE_EMAIL,
    USER_LIVE_PASSWORD,
    VIEWER_LIVE_EMAIL,
    VIEWER_LIVE_PASSWORD,
)

pytestmark = pytest.mark.usefixtures("seed_five_users")


@pytest.mark.asyncio
async def test_jaw_9606_super_admin_login_success(
    live_client: AsyncClient,
) -> None:
    """[JAW-9606] Super Admin can log in with email and password."""
    response = await live_client.post(
        "/api/super-admin/login",
        json={"email": ADMIN_LIVE_EMAIL, "password": ADMIN_LIVE_PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["email"] == ADMIN_LIVE_EMAIL
    assert body["data"]["access_token"]
    assert body["data"]["token_type"] == "bearer"
    assert ADMIN_LIVE_PASSWORD not in response.text


@pytest.mark.asyncio
async def test_jaw_9606_redirect_to_dashboard_on_success(
    live_client: AsyncClient,
) -> None:
    """[JAW-9606] Successful login returns redirect_to for the SPA dashboard."""
    response = await live_client.post(
        "/api/super-admin/login",
        json={"email": ADMIN_LIVE_EMAIL, "password": ADMIN_LIVE_PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["redirect_to"] == "/dashboard"
    assert "dashboard" in body["description"].lower()


@pytest.mark.asyncio
async def test_jaw_9606_invalid_credentials_error_message(
    live_client: AsyncClient,
) -> None:
    """[JAW-9606] Wrong password returns generic 401 error for the UI."""
    response = await live_client.post(
        "/api/super-admin/login",
        json={"email": ADMIN_LIVE_EMAIL, "password": "WrongPass9!"},
    )
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_CREDENTIALS"
    assert body["message"] == "Incorrect email or password"


@pytest.mark.asyncio
async def test_jaw_9606_login_requires_valid_email_format(
    live_client: AsyncClient,
) -> None:
    """[JAW-9606] Malformed email is rejected before credential check."""
    response = await live_client.post(
        "/api/super-admin/login",
        json={"email": "not-an-email", "password": "SomePass1!"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_jaw_9606_empty_email_returns_400(
    live_client: AsyncClient,
) -> None:
    """[JAW-9606] Whitespace-only email returns 400 BAD_REQUEST."""
    response = await live_client.post(
        "/api/super-admin/login",
        json={"email": "   ", "password": "SomePass1!"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BAD_REQUEST"


@pytest.mark.asyncio
async def test_jaw_9606_empty_password_returns_400(
    live_client: AsyncClient,
) -> None:
    """[JAW-9606] Whitespace-only password returns 400 BAD_REQUEST."""
    response = await live_client.post(
        "/api/super-admin/login",
        json={"email": ADMIN_LIVE_EMAIL, "password": "   "},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BAD_REQUEST"


@pytest.mark.asyncio
async def test_jaw_9606_invalid_credentials_unknown_email_401(
    live_client: AsyncClient,
) -> None:
    """[JAW-9606] Unknown email returns 401 INVALID_CREDENTIALS."""
    response = await live_client.post(
        "/api/super-admin/login",
        json={"email": NEW_USER_EMAIL, "password": NEW_USER_PASSWORD},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_regular_user_cannot_super_admin_login(
    live_client: AsyncClient,
) -> None:
    """Non-admin role receives the same 401 as wrong credentials."""
    response = await live_client.post(
        "/api/super-admin/login",
        json={"email": USER_LIVE_EMAIL, "password": USER_LIVE_PASSWORD},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_viewer_cannot_super_admin_login(
    live_client: AsyncClient,
) -> None:
    """Viewer role cannot authenticate via the Super Admin login endpoint."""
    response = await live_client.post(
        "/api/super-admin/login",
        json={"email": VIEWER_LIVE_EMAIL, "password": VIEWER_LIVE_PASSWORD},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_inactive_super_admin_cannot_login(
    live_client: AsyncClient,
) -> None:
    """Inactive accounts are rejected with INVALID_CREDENTIALS."""
    response = await live_client.post(
        "/api/super-admin/login",
        json={"email": INACTIVE_LIVE_EMAIL, "password": INACTIVE_LIVE_PASSWORD},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_edge_case_unicode_password(
    live_client: AsyncClient,
) -> None:
    """Unicode characters in password are handled without server error."""
    response = await live_client.post(
        "/api/super-admin/login",
        json={"email": ADMIN_LIVE_EMAIL, "password": "\u2603\u2603\u2603"},
    )
    assert response.status_code == 401
    assert response.json()["success"] is False


@pytest.mark.asyncio
async def test_login_edge_case_email_case_insensitive(
    live_client: AsyncClient,
) -> None:
    """Email lookup is case-insensitive against PostgreSQL rows."""
    response = await live_client.post(
        "/api/super-admin/login",
        json={"email": ADMIN_LIVE_EMAIL.upper(), "password": ADMIN_LIVE_PASSWORD},
    )
    assert response.status_code == 200
    assert response.json()["email"] == ADMIN_LIVE_EMAIL


@pytest.mark.asyncio
async def test_login_missing_json_fields_422(
    live_client: AsyncClient,
) -> None:
    """Missing password field returns 422 validation envelope."""
    response = await live_client.post(
        "/api/super-admin/login",
        json={"email": ADMIN_LIVE_EMAIL},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert isinstance(body["error"]["details"], list)


@pytest.mark.asyncio
async def test_auth_missing_bearer_token_401(
    live_client: AsyncClient,
) -> None:
    """Protected paths reject requests without Authorization header."""
    response = await live_client.get("/api/v1/protected-placeholder")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_auth_valid_admin_token_passes_middleware(
    live_client: AsyncClient,
    admin_access_token: str,
) -> None:
    """Valid bearer access token satisfies AuthMiddleware on protected paths."""
    response = await live_client.get(
        "/api/v1/protected-placeholder",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_auth_expired_token_401(
    live_client: AsyncClient,
    expired_access_token: str,
) -> None:
    """Expired JWT is rejected by AuthMiddleware."""
    response = await live_client.get(
        "/api/v1/protected-placeholder",
        headers={"Authorization": f"Bearer {expired_access_token}"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_auth_wrong_role_token_still_passes_middleware(
    live_client: AsyncClient,
    user_access_token: str,
) -> None:
    """Middleware validates JWT signature only; role checks happen in dependencies."""
    response = await live_client.get(
        "/api/v1/protected-placeholder",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert response.status_code == 404
