"""Integration tests for Super Admin organization management APIs (JAW-9602)."""

from uuid import uuid4

import pytest
from httpx import AsyncClient


NEW_ORG_NAME = "New Organization"
NEW_ORG_EMAIL = "neworg@example.com"


@pytest.mark.asyncio
async def test_jaw_9602_list_organizations_success(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_organization: dict,
) -> None:
    """[JAW-9602] Super Admin can list organizations."""
    response = await live_client.get(
        "/api/super-admin/organizations",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["total"] >= 2
    items = body["data"]["items"]
    assert len(items) >= 1
    first = items[0]
    assert "id" in first
    assert "name" in first
    assert "organization" in first
    assert "email" in first
    assert "phone" in first
    assert "phone_number" in first
    assert "address" in first


@pytest.mark.asyncio
async def test_jaw_9602_create_organization_success(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_organization: dict,
) -> None:
    """[JAW-9602] Super Admin can add a new organization."""
    response = await live_client.post(
        "/api/super-admin/organizations",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "name": NEW_ORG_NAME,
            "contact_email": NEW_ORG_EMAIL,
            "phone_number": "5551234567",
            "address": "789 Pine St",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    org = body["data"]["organization"]
    assert org["name"] == NEW_ORG_NAME
    assert org["organization"] == NEW_ORG_NAME
    assert org["email"] == NEW_ORG_EMAIL
    assert org["phone"] == "5551234567"
    assert org["address"] == "789 Pine St"


@pytest.mark.asyncio
async def test_jaw_9602_update_organization_success(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_organization: dict,
) -> None:
    """[JAW-9602] Super Admin can edit an existing organization."""
    target = seed_organization["active"]
    response = await live_client.put(
        f"/api/super-admin/organizations/{target.id}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "name": "Updated Organization",
            "contact_email": "updated@example.com",
            "phone_number": "9998887777",
            "address": "456 Oak Ave",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    org = body["data"]["organization"]
    assert org["name"] == "Updated Organization"
    assert org["email"] == "updated@example.com"
    assert org["phone"] == "9998887777"


@pytest.mark.asyncio
async def test_jaw_9602_remove_organization_success(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_organization: dict,
) -> None:
    """[JAW-9602] Super Admin can remove an organization."""
    target = seed_organization["active"]
    response = await live_client.delete(
        f"/api/super-admin/organizations/{target.id}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["organization"]["is_active"] is False


@pytest.mark.asyncio
async def test_jaw_9602_create_invalid_data_returns_422(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_organization: dict,
) -> None:
    """[JAW-9602] Invalid organization data returns validation error."""
    response = await live_client.post(
        "/api/super-admin/organizations",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "name": "",
            "contact_email": "not-an-email",
            "phone_number": "abc",
            "address": "",
        },
    )
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_jaw_9602_create_duplicate_name_returns_409(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_organization: dict,
) -> None:
    """[JAW-9602] Duplicate organization name returns conflict error."""
    response = await live_client.post(
        "/api/super-admin/organizations",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "name": "Organization Name",
            "contact_email": "duplicate@example.com",
            "phone_number": "1111111111",
            "address": "123 Duplicate St",
        },
    )
    assert response.status_code == 409
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "ORGANIZATION_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_jaw_9602_update_organization_not_found_returns_404(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_organization: dict,
) -> None:
    """[JAW-9602] Updating unknown organization returns 404."""
    response = await live_client.put(
        f"/api/super-admin/organizations/{uuid4()}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"name": "Missing"},
    )
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "ORGANIZATION_NOT_FOUND"


@pytest.mark.asyncio
async def test_jaw_9602_delete_organization_not_found_returns_404(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_organization: dict,
) -> None:
    """[JAW-9602] Removing unknown organization returns 404."""
    response = await live_client.delete(
        f"/api/super-admin/organizations/{uuid4()}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "ORGANIZATION_NOT_FOUND"


@pytest.mark.asyncio
async def test_jaw_9602_non_admin_returns_403(
    live_client: AsyncClient,
    user_access_token: str,
    seed_organization: dict,
) -> None:
    """[JAW-9602] Non-admin users cannot access organization management APIs."""
    response = await live_client.get(
        "/api/super-admin/organizations",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert response.status_code == 403
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "FORBIDDEN"
