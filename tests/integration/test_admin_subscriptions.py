"""Live PostgreSQL integration tests for admin subscription plans (JAW-9465)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.db.session import AsyncSessionLocal


@pytest.fixture(autouse=True)
async def clear_subscription_plans(postgres_schema: None) -> None:
    """Ensure each test starts with an empty plan catalog."""
    async with AsyncSessionLocal() as session:
        await session.execute(text("TRUNCATE TABLE subscription_plans RESTART IDENTITY CASCADE"))
        await session.commit()


@pytest.mark.asyncio
async def test_list_plans_requires_super_admin(
    db_client: AsyncClient,
    user_headers: dict[str, str],
) -> None:
    """Non-admin tokens cannot list subscription plans."""
    response = await db_client.get(
        "/api/v1/subscriptions",
        headers=user_headers,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_create_and_get_plan(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Super Admin can create and fetch a subscription plan."""
    create = await db_client.post(
        "/api/v1/subscriptions",
        headers=admin_headers,
        json={
            "name": "Team Plan",
            "description": "For entire organizations",
            "price": 49.99,
            "billing_cycle": "Monthly",
            "is_published": True,
        },
    )
    assert create.status_code == 201
    body = create.json()
    assert body["success"] is True
    assert body["description"]
    plan_id = body["data"]["id"]
    assert body["data"]["billing_cycle"] == "Monthly"

    fetch = await db_client.get(
        f"/api/v1/subscriptions/{plan_id}",
        headers=admin_headers,
    )
    assert fetch.status_code == 200
    assert fetch.json()["data"]["name"] == "Team Plan"


@pytest.mark.asyncio
async def test_update_plan(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Super Admin can edit an existing plan."""
    create = await db_client.post(
        "/api/v1/subscriptions",
        headers=admin_headers,
        json={
            "name": "Basic",
            "price": 9.99,
            "billing_cycle": "Monthly",
        },
    )
    plan_id = create.json()["data"]["id"]

    update = await db_client.put(
        f"/api/v1/subscriptions/{plan_id}",
        headers=admin_headers,
        json={"price": 14.99, "billing_cycle": "Yearly"},
    )
    assert update.status_code == 200
    assert float(update.json()["data"]["price"]) == 14.99
    assert update.json()["data"]["billing_cycle"] == "Yearly"


@pytest.mark.asyncio
async def test_delete_plan_unpublishes(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """DELETE soft-removes a plan from the published catalog."""
    create = await db_client.post(
        "/api/v1/subscriptions",
        headers=admin_headers,
        json={
            "name": "Legacy Plan",
            "price": 5.99,
            "billing_cycle": "Monthly",
            "is_published": True,
        },
    )
    plan_id = create.json()["data"]["id"]

    delete = await db_client.delete(
        f"/api/v1/subscriptions/{plan_id}",
        headers=admin_headers,
    )
    assert delete.status_code == 200
    assert delete.json()["data"]["is_published"] is False

    published = await db_client.get(
        "/api/v1/subscriptions?published_only=true",
        headers=admin_headers,
    )
    assert published.status_code == 200
    assert published.json()["data"]["items"] == []


@pytest.mark.asyncio
async def test_create_duplicate_name_returns_conflict(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Duplicate plan names return 409 SUBSCRIPTION_PLAN_ALREADY_EXISTS."""
    payload = {
        "name": "Unique Plan",
        "price": 12.00,
        "billing_cycle": "Monthly",
    }
    first = await db_client.post(
        "/api/v1/subscriptions",
        headers=admin_headers,
        json=payload,
    )
    assert first.status_code == 201

    second = await db_client.post(
        "/api/v1/subscriptions",
        headers=admin_headers,
        json=payload,
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "SUBSCRIPTION_PLAN_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_subscriptions_alias_path(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Ticket path GET /api/subscriptions works via alias mount."""
    response = await db_client.get(
        "/api/subscriptions",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_subscriptions_documented_in_openapi(db_client: AsyncClient) -> None:
    """OpenAPI includes admin subscription plan operations."""
    response = await db_client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/subscriptions" in paths
    assert "post" in paths["/api/v1/subscriptions"]
    assert "/api/subscriptions" in paths
