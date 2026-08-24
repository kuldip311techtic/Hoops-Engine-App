"""Integration tests for Super Admin subscription plan APIs (JAW-9604)."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

NEW_PLAN_NAME = "Pro Plan"
NEW_PLAN_PRICE = 29.99


@pytest.mark.asyncio
async def test_jaw_9604_list_subscriptions_success(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_subscription_plan: dict,
) -> None:
    """[JAW-9604] Super Admin can list subscription plans."""
    response = await live_client.get(
        "/api/super-admin/subscriptions",
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
    assert "price" in first
    assert "billing_cycle" in first
    assert "duration" in first
    assert "status" in first
    assert "description" in first


@pytest.mark.asyncio
async def test_jaw_9604_create_subscription_success(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_subscription_plan: dict,
) -> None:
    """[JAW-9604] Super Admin can add a new subscription plan."""
    response = await live_client.post(
        "/api/super-admin/subscriptions",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "name": NEW_PLAN_NAME,
            "description": "Premium coaching access.",
            "price": NEW_PLAN_PRICE,
            "billing_cycle": "monthly",
            "is_published": True,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    plan = body["data"]["subscription_plan"]
    assert plan["name"] == NEW_PLAN_NAME
    assert float(plan["price"]) == NEW_PLAN_PRICE
    assert plan["billing_cycle"] == "monthly"
    assert plan["duration"] == "monthly"
    assert plan["status"] == "published"


@pytest.mark.asyncio
async def test_jaw_9604_update_subscription_success(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_subscription_plan: dict,
) -> None:
    """[JAW-9604] Super Admin can edit an existing subscription plan."""
    target = seed_subscription_plan["published"]
    response = await live_client.put(
        f"/api/super-admin/subscriptions/{target.id}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "name": "Updated Basic Plan",
            "price": 12.99,
            "billing_cycle": "yearly",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    plan = body["data"]["subscription_plan"]
    assert plan["name"] == "Updated Basic Plan"
    assert float(plan["price"]) == 12.99
    assert plan["billing_cycle"] == "yearly"


@pytest.mark.asyncio
async def test_jaw_9604_remove_subscription_success(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_subscription_plan: dict,
) -> None:
    """[JAW-9604] Super Admin can remove a subscription plan."""
    target = seed_subscription_plan["published"]
    response = await live_client.delete(
        f"/api/super-admin/subscriptions/{target.id}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    plan = body["data"]["subscription_plan"]
    assert plan["is_published"] is False
    assert plan["status"] == "unpublished"


@pytest.mark.asyncio
async def test_jaw_9604_create_invalid_data_returns_422(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_subscription_plan: dict,
) -> None:
    """[JAW-9604] Invalid subscription data returns validation error."""
    response = await live_client.post(
        "/api/super-admin/subscriptions",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "name": "",
            "price": -1,
            "billing_cycle": "weekly",
        },
    )
    assert response.status_code in (400, 422)
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] in ("VALIDATION_ERROR", "BAD_REQUEST")


@pytest.mark.asyncio
async def test_jaw_9604_create_duplicate_name_returns_409(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_subscription_plan: dict,
) -> None:
    """[JAW-9604] Duplicate subscription plan name returns conflict error."""
    response = await live_client.post(
        "/api/super-admin/subscriptions",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "name": "Basic Plan",
            "price": 1.99,
            "billing_cycle": "monthly",
        },
    )
    assert response.status_code == 409
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "SUBSCRIPTION_PLAN_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_jaw_9604_update_not_found_returns_404(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_subscription_plan: dict,
) -> None:
    """[JAW-9604] Updating unknown subscription plan returns 404."""
    response = await live_client.put(
        f"/api/super-admin/subscriptions/{uuid4()}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"name": "Missing Plan"},
    )
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "SUBSCRIPTION_PLAN_NOT_FOUND"


@pytest.mark.asyncio
async def test_jaw_9604_delete_not_found_returns_404(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_subscription_plan: dict,
) -> None:
    """[JAW-9604] Removing unknown subscription plan returns 404."""
    response = await live_client.delete(
        f"/api/super-admin/subscriptions/{uuid4()}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "SUBSCRIPTION_PLAN_NOT_FOUND"


@pytest.mark.asyncio
async def test_jaw_9604_unauthenticated_returns_401(
    live_client: AsyncClient,
    seed_subscription_plan: dict,
) -> None:
    """[JAW-9604] Missing Bearer token returns 401."""
    response = await live_client.get("/api/super-admin/subscriptions")
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_jaw_9604_non_admin_returns_403(
    live_client: AsyncClient,
    user_access_token: str,
    seed_subscription_plan: dict,
) -> None:
    """[JAW-9604] Non-admin users cannot access subscription management APIs."""
    response = await live_client.get(
        "/api/super-admin/subscriptions",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert response.status_code == 403
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_jaw_9604_published_only_filter(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_subscription_plan: dict,
) -> None:
    """[JAW-9604] published_only=true returns only published plans."""
    response = await live_client.get(
        "/api/super-admin/subscriptions?published_only=true",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert all(item["is_published"] is True for item in items)
    assert all(item["status"] == "published" for item in items)
