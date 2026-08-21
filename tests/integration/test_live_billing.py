"""Live billing-cycle and webhook integration tests (HMAC local, no Stripe/Auth0)."""

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models.subscription import Subscription
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.billing_service import BillingService
from tests.conftest import USER_EMAIL


def _sign(secret: str, body: bytes) -> str:
    """Hex HMAC-SHA256 used by the local Auth0/billing adapters."""
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


async def test_cancelled_subscription_retains_access_until_period_end(
    client, db_session, settings
) -> None:
    """JAW-9470: cancel keeps has_access True until access_until."""
    future = datetime.now(timezone.utc) + timedelta(days=10)
    payload = {
        "type": "customer.subscription.deleted",
        "email": USER_EMAIL,
        "access_until": future.isoformat(),
        "provider_ref": "sub_test_1",
        "description": "Cancelled; access retained until period end",
    }
    raw = json.dumps(payload).encode("utf-8")
    response = await client.post(
        "/api/v1/webhooks/billing",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Signature": _sign(settings.billing_webhook_secret, raw),
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["accepted"] is True
    assert body["data"]["email"] == USER_EMAIL

    service = BillingService(SubscriptionRepository(db_session))
    snapshot = await service.access_for_email(USER_EMAIL)
    assert snapshot.has_access is True
    assert snapshot.status == "cancelled"
    assert snapshot.access_until is not None


async def test_expired_subscription_denies_access(db_session) -> None:
    """After access_until, cancelled subscriptions are expired."""
    past = datetime.now(timezone.utc) - timedelta(days=1)
    repo = SubscriptionRepository(db_session)
    await repo.upsert_cancelled(
        email="expired@test.com",
        access_until=past,
        provider_ref="sub_expired",
        cancelled_at=past,
    )
    await db_session.commit()
    service = BillingService(repo)
    snapshot = await service.access_for_email("expired@test.com")
    assert snapshot.has_access is False
    assert snapshot.status == "expired"


async def test_billing_webhook_unsigned_401(client) -> None:
    """Billing webhook without HMAC is unauthorized."""
    response = await client.post(
        "/api/v1/webhooks/billing",
        json={
            "type": "customer.subscription.deleted",
            "email": USER_EMAIL,
        },
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_WEBHOOK_SIGNATURE"


async def test_billing_webhook_wrong_hmac_401(client) -> None:
    """Wrong HMAC is rejected without applying cancellation."""
    payload = {
        "type": "customer.subscription.deleted",
        "email": USER_EMAIL,
    }
    raw = json.dumps(payload).encode("utf-8")
    response = await client.post(
        "/api/v1/webhooks/billing",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Signature": "deadbeef",
        },
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_WEBHOOK_SIGNATURE"


async def test_auth0_webhook_valid_hmac(client, settings) -> None:
    """Auth0 adapter accepts a correctly signed local HMAC (no Auth0 HTTP)."""
    payload = {
        "type": "scim.user.updated",
        "email": USER_EMAIL,
        "description": "User password changed",
    }
    raw = json.dumps(payload).encode("utf-8")
    response = await client.post(
        "/api/v1/webhooks/auth0",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Signature": _sign(settings.auth0_webhook_secret, raw),
        },
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"]["accepted"] is True


async def test_auth0_webhook_missing_signature(client) -> None:
    """Auth0 webhook without a signature is 401."""
    response = await client.post(
        "/api/v1/webhooks/auth0",
        json={"type": "scim.user.updated", "email": USER_EMAIL},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_WEBHOOK_SIGNATURE"


async def test_subscription_row_persisted_after_webhook(
    client, db_session, settings
) -> None:
    """Billing webhook writes a subscriptions row keyed by email."""
    future = datetime.now(timezone.utc) + timedelta(days=5)
    payload = {
        "type": "customer.subscription.deleted",
        "email": "coach@test.com",
        "access_until": future.isoformat(),
        "provider_ref": "sub_coach",
    }
    raw = json.dumps(payload).encode("utf-8")
    response = await client.post(
        "/api/v1/webhooks/billing",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Signature": _sign(settings.billing_webhook_secret, raw),
        },
    )
    assert response.status_code == 200
    result = await db_session.execute(
        select(Subscription).where(Subscription.email == "coach@test.com")
    )
    row = result.scalar_one()
    assert row.status == "cancelled"
    assert row.provider_ref == "sub_coach"
