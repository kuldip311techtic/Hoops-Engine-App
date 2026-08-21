"""Live PostgreSQL integration tests for admin users (JAW-9460)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.conftest import LIVE_NEW_EMAIL, LIVE_NEW_PASSWORD, LIVE_USER_EMAIL

# --- JAW-9460 acceptance criteria ---


@pytest.mark.asyncio
async def test_jaw_9460_view_users(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
    seeded_users: dict,
) -> None:
    """[JAW-9460] View list of users."""
    response = await db_client.get("/api/v1/users", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["page"] == 1
    assert data["total"] >= 4
    emails = {row["email"] for row in data["items"]}
    assert seeded_users["admin"].email in emails


@pytest.mark.asyncio
async def test_jaw_9460_add_user(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
    new_user_registration_payload: dict[str, str],
) -> None:
    """[JAW-9460] Add new user."""
    response = await db_client.post(
        "/api/v1/users",
        headers=admin_headers,
        json=new_user_registration_payload,
    )
    assert response.status_code == 201
    user = response.json()["data"]["user"]
    assert user["email"] == LIVE_NEW_EMAIL
    assert user["role"] == "Coach"


@pytest.mark.asyncio
async def test_jaw_9460_edit_user(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """[JAW-9460] Edit existing user."""
    create = await db_client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "first_name": "Edit",
            "last_name": "Target",
            "email": "edit.target@example.com",
            "password": LIVE_NEW_PASSWORD,
            "role": "Player",
        },
    )
    user_id = create.json()["data"]["user"]["id"]
    update = await db_client.put(
        f"/api/v1/users/{user_id}",
        headers=admin_headers,
        json={"first_name": "Edited", "role": "Coach"},
    )
    assert update.status_code == 200
    updated = update.json()["data"]["user"]
    assert updated["name"] == "Edited Target"
    assert updated["role"] == "Coach"


@pytest.mark.asyncio
async def test_jaw_9460_remove_user(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """[JAW-9460] Remove user (soft-deactivate)."""
    create = await db_client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "first_name": "Remove",
            "last_name": "Target",
            "email": "remove.target@example.com",
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


@pytest.mark.asyncio
async def test_jaw_9460_active_only_excludes_inactive(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
    seeded_users: dict,
) -> None:
    """[JAW-9460] active_only excludes deactivated accounts."""
    response = await db_client.get(
        "/api/v1/users?active_only=true",
        headers=admin_headers,
    )
    assert response.status_code == 200
    emails = {row["email"] for row in response.json()["data"]["items"]}
    assert seeded_users["inactive"].email not in emails
    assert seeded_users["user"].email in emails


@pytest.mark.asyncio
async def test_jaw_9460_openapi_documents_users(db_client: AsyncClient) -> None:
    """[JAW-9460] OpenAPI includes user admin operations."""
    response = await db_client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/users" in paths
    assert "put" in paths["/api/v1/users/{user_id}"]


# --- Auth ---


@pytest.mark.asyncio
async def test_users_missing_token_401(
    db_client: AsyncClient,
    missing_auth_headers: dict[str, str],
) -> None:
    response = await db_client.get("/api/v1/users", headers=missing_auth_headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_users_viewer_forbidden(
    db_client: AsyncClient,
    viewer_headers: dict[str, str],
) -> None:
    response = await db_client.get("/api/v1/users", headers=viewer_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cannot_delete_own_account(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
    seeded_users: dict,
) -> None:
    admin_id = seeded_users["admin"].id
    response = await db_client.delete(
        f"/api/v1/users/{admin_id}",
        headers=admin_headers,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CANNOT_REMOVE_SELF"


# --- Edge cases ---


@pytest.mark.asyncio
async def test_create_user_weak_password_422(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await db_client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "first_name": "Weak",
            "last_name": "Pass",
            "email": "weak@example.com",
            "password": "short",
            "role": "User",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_user_unicode_names(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await db_client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "first_name": "José",
            "last_name": "García",
            "email": "jose.garcia@example.com",
            "password": LIVE_NEW_PASSWORD,
            "role": "Coach",
        },
    )
    assert response.status_code == 201
    assert response.json()["data"]["user"]["name"] == "José García"


# --- Error cases ---


@pytest.mark.asyncio
async def test_get_user_not_found(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await db_client.get(
        f"/api/v1/users/{uuid4()}",
        headers=admin_headers,
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "USER_NOT_FOUND"


@pytest.mark.asyncio
async def test_create_duplicate_email_conflict(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await db_client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "first_name": "Dup",
            "last_name": "User",
            "email": LIVE_USER_EMAIL,
            "password": LIVE_NEW_PASSWORD,
            "role": "Coach",
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_users_alias_path(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await db_client.get("/api/users", headers=admin_headers)
    assert response.status_code == 200
    assert "page" in response.json()["data"]
