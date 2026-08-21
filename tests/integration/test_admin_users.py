"""Live PostgreSQL integration tests for admin users (JAW-9460)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import LIVE_NEW_EMAIL, LIVE_NEW_PASSWORD, LIVE_USER_EMAIL


@pytest.mark.asyncio
async def test_list_users_requires_super_admin(
    db_client: AsyncClient,
    user_headers: dict[str, str],
) -> None:
    """Non-admin tokens cannot list users."""
    response = await db_client.get(
        "/api/v1/users",
        headers=user_headers,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_create_and_get_user(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Super Admin can create and fetch a user."""
    create = await db_client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "first_name": "John",
            "last_name": "Doe",
            "email": LIVE_NEW_EMAIL,
            "password": LIVE_NEW_PASSWORD,
            "role": "Coach",
        },
    )
    assert create.status_code == 201
    body = create.json()
    assert body["success"] is True
    assert body["description"]
    user = body["data"]["user"]
    assert user["id"]
    assert user["name"] == "John Doe"
    assert user["role"] == "Coach"
    assert user["email"] == LIVE_NEW_EMAIL

    fetch = await db_client.get(
        f"/api/v1/users/{user['id']}",
        headers=admin_headers,
    )
    assert fetch.status_code == 200
    assert fetch.json()["data"]["user"]["email"] == LIVE_NEW_EMAIL


@pytest.mark.asyncio
async def test_update_user(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Super Admin can edit an existing user."""
    create = await db_client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane.smith@example.com",
            "password": LIVE_NEW_PASSWORD,
            "role": "Player",
        },
    )
    user_id = create.json()["data"]["user"]["id"]

    update = await db_client.put(
        f"/api/v1/users/{user_id}",
        headers=admin_headers,
        json={
            "first_name": "Janet",
            "role": "Coach",
        },
    )
    assert update.status_code == 200
    updated = update.json()["data"]["user"]
    assert updated["name"] == "Janet Smith"
    assert updated["role"] == "Coach"


@pytest.mark.asyncio
async def test_delete_user_soft_deactivates(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """DELETE soft-removes a user from the active roster."""
    create = await db_client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "first_name": "Delete",
            "last_name": "Me",
            "email": "delete.me@example.com",
            "password": LIVE_NEW_PASSWORD,
            "role": "User",
        },
    )
    user_id = create.json()["data"]["user"]["id"]

    delete = await db_client.delete(
        f"/api/v1/users/{user_id}",
        headers=admin_headers,
    )
    assert delete.status_code == 200
    assert delete.json()["data"]["user"]["is_active"] is False

    active_list = await db_client.get(
        "/api/v1/users?active_only=true",
        headers=admin_headers,
    )
    emails = [row["email"] for row in active_list.json()["data"]["items"]]
    assert "delete.me@example.com" not in emails


@pytest.mark.asyncio
async def test_cannot_delete_own_account(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
    seeded_users: dict,
) -> None:
    """Super Admin cannot remove their own account."""
    admin_id = seeded_users["admin"].id
    response = await db_client.delete(
        f"/api/v1/users/{admin_id}",
        headers=admin_headers,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CANNOT_REMOVE_SELF"


@pytest.mark.asyncio
async def test_create_duplicate_email_returns_conflict(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Duplicate emails return 409 EMAIL_ALREADY_EXISTS."""
    payload = {
        "first_name": "Dup",
        "last_name": "User",
        "email": LIVE_USER_EMAIL,
        "password": LIVE_NEW_PASSWORD,
        "role": "Coach",
    }
    response = await db_client.post(
        "/api/v1/users",
        headers=admin_headers,
        json=payload,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_users_alias_path(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Ticket path GET /api/users works via alias mount."""
    response = await db_client.get(
        "/api/users",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert "page" in response.json()["data"]


@pytest.mark.asyncio
async def test_users_documented_in_openapi(db_client: AsyncClient) -> None:
    """OpenAPI includes admin user operations."""
    response = await db_client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/users" in paths
    assert "post" in paths["/api/v1/users"]
    assert "/api/users" in paths
