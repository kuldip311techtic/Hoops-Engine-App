"""Live PostgreSQL webhook tests with HMAC computed locally (no Auth0/billing HTTP)."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.subscription import SubscriptionStatus
from app.models.user import User
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from tests.conftest import LIVE_USER_EMAIL


def _sign(secret: str, body: bytes) -> str:
    """HMAC-SHA256 hex digest matching Auth0Client/BillingClient."""
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_auth0_webhook_valid_signature_no_external_call(
    db_client: AsyncClient,
) -> None:
    """Auth0 webhook accepts a locally signed body; Auth0 HTTP is never called."""
    payload = {"event": "ping", "user_email": None, "environment": "sandbox"}
    raw = json.dumps(payload).encode()
    secret = get_settings().auth0_webhook_secret
    response = await db_client.post(
        "/api/v1/webhooks/auth0",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-Auth0-Signature": _sign(secret, raw),
        },
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"]["accepted"] is True


@pytest.mark.asyncio
async def test_auth0_webhook_missing_signature(db_client: AsyncClient) -> None:
    """Missing X-Auth0-Signature is 401 or 422."""
    response = await db_client.post(
        "/api/v1/webhooks/auth0",
        json={"event": "ping", "environment": "sandbox"},
    )
    assert response.status_code in (401, 422)


@pytest.mark.asyncio
async def test_billing_webhook_wrong_hmac(db_client: AsyncClient) -> None:
    """Wrong billing HMAC is 401 INVALID_SIGNATURE."""
    payload = {
        "user_email": LIVE_USER_EMAIL,
        "status": "CANCELLED",
        "current_period_end": "2099-01-01T00:00:00Z",
    }
    raw = json.dumps(payload).encode()
    response = await db_client.post(
        "/api/v1/webhooks/billing",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-Billing-Signature": "00" * 32,
        },
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_SIGNATURE"


@pytest.mark.asyncio
async def test_billing_webhook_cancelled_retains_access(
    db_client: AsyncClient,
    seeded_users: dict[str, User],
) -> None:
    """Billing CANCELLED webhook stores period end; has_access remains True."""
    end = (datetime.now(timezone.utc) + timedelta(days=14)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    payload = {
        "user_email": LIVE_USER_EMAIL,
        "status": "CANCELLED",
        "current_period_end": end,
    }
    raw = json.dumps(payload).encode()
    secret = get_settings().billing_webhook_secret
    response = await db_client.post(
        "/api/v1/webhooks/billing",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-Billing-Signature": _sign(secret, raw),
        },
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "CANCELLED"
    async with AsyncSessionLocal() as session:
        service = AuthService(UserRepository(session), SubscriptionRepository(session))
        user = await UserRepository(session).get_by_email(LIVE_USER_EMAIL)
        assert user is not None
        assert await service.has_access(user) is True
        sub = await SubscriptionRepository(session).get_by_user_id(user.id)
        assert sub is not None
        assert sub.status == SubscriptionStatus.CANCELLED
