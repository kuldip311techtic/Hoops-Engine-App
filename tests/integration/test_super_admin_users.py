"""Integration tests for Super Admin user management APIs (JAW-9603)."""

import os
import secrets
from uuid import uuid4

import pytest
from httpx import AsyncClient

NEW_COACH_EMAIL = "newcoach@test.com"
NEW_COACH_PASSWORD = os.environ.get("TEST_NEW_COACH_PASSWORD") or f"Aa1!{secrets.token_hex(8)}"


@pytest.mark.asyncio
async def test_jaw_9603_list_users_success(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_five_users: dict,
) -> None:
    """[JAW-9603] Super Admin can list users with pagination metadata."""
    response = await live_client.get(
        "/api/super-admin/users",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["total"] >= 4
    items = body["data"]["items"]
    assert len(items) >= 1
    first = items[0]
    assert "id" in first
    assert "name" in first
    assert "email" in first
    assert "role" in first
    assert "roles" in first


@pytest.mark.asyncio
async def test_jaw_9603_create_user_success(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_five_users: dict,
) -> None:
    """[JAW-9603] Super Admin can add a new user."""
    response = await live_client.post(
        "/api/super-admin/users",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "first_name": "John",
            "last_name": "Doe",
            "email": NEW_COACH_EMAIL,
            "password": NEW_COACH_PASSWORD,
            "role": "Coach",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    user = body["data"]["user"]
    assert user["email"] == NEW_COACH_EMAIL
    assert user["role"] == "Coach"
    assert user["roles"] == ["Coach"]
    assert user["name"] == "John Doe"


@pytest.mark.asyncio
async def test_jaw_9603_update_user_success(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_five_users: dict,
) -> None:
    """[JAW-9603] Super Admin can edit an existing user."""
    target = seed_five_users["user"]
    response = await live_client.put(
        f"/api/super-admin/users/{target.id}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "first_name": "Updated",
            "last_name": "Name",
            "role": "Viewer",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    user = body["data"]["user"]
    assert user["first_name"] == "Updated"
    assert user["role"] == "Viewer"


@pytest.mark.asyncio
async def test_jaw_9603_remove_user_success(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_five_users: dict,
) -> None:
    """[JAW-9603] Super Admin can remove a user."""
    target = seed_five_users["user"]
    response = await live_client.delete(
        f"/api/super-admin/users/{target.id}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["user"]["is_active"] is False


@pytest.mark.asyncio
async def test_jaw_9603_create_user_invalid_data_returns_422(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_five_users: dict,
) -> None:
    """[JAW-9603] Weak password returns validation error."""
    response = await live_client.post(
        "/api/super-admin/users",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "first_name": "Bad",
            "last_name": "Password",
            "email": "weak@test.com",
            "password": "password123",
            "role": "Coach",
        },
    )
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_jaw_9603_create_duplicate_email_returns_409(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_five_users: dict,
) -> None:
    """[JAW-9603] Duplicate email returns conflict error."""
    response = await live_client.post(
        "/api/super-admin/users",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "first_name": "Dup",
            "last_name": "Email",
            "email": "user@test.com",
            "password": NEW_COACH_PASSWORD,
            "role": "Coach",
        },
    )
    assert response.status_code == 409
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_jaw_9603_update_user_not_found_returns_404(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_five_users: dict,
) -> None:
    """[JAW-9603] Updating unknown user returns 404."""
    response = await live_client.put(
        f"/api/super-admin/users/{uuid4()}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"first_name": "Missing"},
    )
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "USER_NOT_FOUND"


@pytest.mark.asyncio
async def test_jaw_9603_non_admin_returns_403(
    live_client: AsyncClient,
    user_access_token: str,
    seed_five_users: dict,
) -> None:
    """[JAW-9603] Non-admin users cannot access user management APIs."""
    response = await live_client.get(
        "/api/super-admin/users",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert response.status_code == 403
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_jaw_9603_cannot_remove_own_account(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_five_users: dict,
) -> None:
    """[JAW-9603] Super Admin cannot remove their own account."""
    admin = seed_five_users["admin"]
    response = await live_client.delete(
        f"/api/super-admin/users/{admin.id}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert response.status_code == 403
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "CANNOT_REMOVE_SELF"
