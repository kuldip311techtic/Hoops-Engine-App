"""Live PostgreSQL integration tests for admin organizations (JAW-9457)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.db.session import AsyncSessionLocal


@pytest.fixture(autouse=True)
async def clear_organizations(postgres_schema: None) -> None:
    """Ensure each test starts with an empty organizations table."""
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("TRUNCATE TABLE organizations RESTART IDENTITY CASCADE")
        )
        await session.commit()


@pytest.mark.asyncio
async def test_list_organizations_requires_super_admin(
    db_client: AsyncClient,
    user_headers: dict[str, str],
) -> None:
    """Non-admin tokens cannot list organizations."""
    response = await db_client.get(
        "/api/v1/organizations",
        headers=user_headers,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_create_and_get_organization(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Super Admin can create and fetch an organization."""
    create = await db_client.post(
        "/api/v1/organizations",
        headers=admin_headers,
        json={
            "name": "Central Hoops",
            "contact_email": "central@example.com",
            "phone_number": "5551234567",
            "address": "100 Court St",
            "description": "Central region org",
            "is_published": True,
        },
    )
    assert create.status_code == 201
    body = create.json()
    assert body["success"] is True
    assert body["description"]
    org = body["data"]["organization"]
    assert org["id"]
    assert org["email"] == "central@example.com"
    assert org["phone"] == "5551234567"
    assert org["phone_number"] == "5551234567"

    fetch = await db_client.get(
        f"/api/v1/organizations/{org['id']}",
        headers=admin_headers,
    )
    assert fetch.status_code == 200
    assert fetch.json()["data"]["organization"]["name"] == "Central Hoops"


@pytest.mark.asyncio
async def test_update_organization(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Super Admin can edit an existing organization."""
    create = await db_client.post(
        "/api/v1/organizations",
        headers=admin_headers,
        json={
            "name": "East Hoops",
            "contact_email": "east@example.com",
            "phone_number": "5550001111",
            "address": "200 Lane",
        },
    )
    org_id = create.json()["data"]["organization"]["id"]

    update = await db_client.put(
        f"/api/v1/organizations/{org_id}",
        headers=admin_headers,
        json={
            "name": "East Hoops Elite",
            "phone_number": "5550002222",
            "address": "201 Lane",
        },
    )
    assert update.status_code == 200
    updated = update.json()["data"]["organization"]
    assert updated["name"] == "East Hoops Elite"
    assert updated["phone_number"] == "5550002222"


@pytest.mark.asyncio
async def test_delete_organization_deactivates(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """DELETE soft-removes an organization from the active catalog."""
    create = await db_client.post(
        "/api/v1/organizations",
        headers=admin_headers,
        json={
            "name": "Remove Me Org",
            "contact_email": "remove@example.com",
            "phone_number": "5559998888",
            "address": "9 Delete Ave",
            "is_published": True,
        },
    )
    org_id = create.json()["data"]["organization"]["id"]

    delete = await db_client.delete(
        f"/api/v1/organizations/{org_id}",
        headers=admin_headers,
    )
    assert delete.status_code == 200
    assert delete.json()["data"]["organization"]["is_active"] is False

    published = await db_client.get(
        "/api/v1/organizations?published_only=true",
        headers=admin_headers,
    )
    assert published.status_code == 200
    assert published.json()["data"]["items"] == []


@pytest.mark.asyncio
async def test_create_duplicate_name_returns_conflict(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Duplicate organization names return 409 ORGANIZATION_ALREADY_EXISTS."""
    payload = {
        "name": "Unique Org",
        "contact_email": "unique@example.com",
        "phone_number": "5554443333",
        "address": "3 Unique Rd",
    }
    first = await db_client.post(
        "/api/v1/organizations",
        headers=admin_headers,
        json=payload,
    )
    assert first.status_code == 201

    second = await db_client.post(
        "/api/v1/organizations",
        headers=admin_headers,
        json={
            **payload,
            "contact_email": "other@example.com",
        },
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "ORGANIZATION_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_organizations_alias_path(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Ticket path GET /api/organizations works via alias mount."""
    response = await db_client.get(
        "/api/organizations",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_organizations_documented_in_openapi(db_client: AsyncClient) -> None:
    """OpenAPI includes admin organization operations."""
    response = await db_client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/organizations" in paths
    assert "post" in paths["/api/v1/organizations"]
    assert "/api/organizations" in paths
