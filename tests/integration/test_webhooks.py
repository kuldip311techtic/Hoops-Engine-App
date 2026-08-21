"""Webhook HTTP tests."""

import hashlib
import hmac
import json

import pytest
from httpx import AsyncClient

from app.core.config import get_settings


def _sign(secret: str, body: bytes) -> str:
    """HMAC-SHA256 hex digest."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.mark.asyncio
async def test_auth0_webhook_missing_signature(client: AsyncClient) -> None:
    """Missing signature header is a validation/auth error."""
    response = await client.post(
        "/api/v1/webhooks/auth0",
        json={"event": "ping"},
    )
    assert response.status_code in (401, 422)


@pytest.mark.asyncio
async def test_auth0_webhook_valid_hmac(client: AsyncClient) -> None:
    """Valid HMAC is accepted."""
    payload = {"event": "ping", "user_email": None, "environment": "sandbox"}
    raw = json.dumps(payload).encode()
    secret = get_settings().auth0_webhook_secret
    response = await client.post(
        "/api/v1/webhooks/auth0",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-Auth0-Signature": _sign(secret, raw),
        },
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_billing_webhook_wrong_hmac_401(client: AsyncClient) -> None:
    """Wrong billing HMAC is 401."""
    payload = {
        "user_email": "player@example.com",
        "status": "CANCELLED",
        "current_period_end": "2099-01-01T00:00:00Z",
    }
    raw = json.dumps(payload).encode()
    response = await client.post(
        "/api/v1/webhooks/billing",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-Billing-Signature": "00" * 32,
        },
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_SIGNATURE"
