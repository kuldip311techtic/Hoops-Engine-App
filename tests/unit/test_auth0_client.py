"""Auth0 and billing webhook signature tests."""

import hashlib
import hmac

import pytest

from app.clients.auth0_client import Auth0Client
from app.clients.billing_client import BillingClient
from app.core.config import Settings
from app.exceptions import AppError, UnauthorizedError


def _settings(**overrides) -> Settings:
    values = {
        "database_url": "postgresql+asyncpg://u:p@localhost/db",
        "test_database_url": "postgresql+asyncpg://u:p@localhost/db_test",
        "secret_key": "s",
        "jwt_secret_key": "k",
        "auth0_webhook_secret": "auth0-secret",
        "billing_webhook_secret": "billing-secret",
        "environment": "development",
    }
    values.update(overrides)
    return Settings(**values)


def _sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def test_auth0_sandbox_vs_production() -> None:
    """Non-production environments map to sandbox."""
    client = Auth0Client(settings=_settings(environment="development"))
    assert client.runtime_environment() == "sandbox"
    prod = Auth0Client(settings=_settings(environment="production"))
    assert prod.runtime_environment() == "production"


def test_auth0_valid_signature() -> None:
    """Matching HMAC is accepted."""
    settings = _settings()
    body = b'{"type":"x"}'
    Auth0Client(settings=settings).verify_webhook_signature(
        body=body,
        signature=_sign("auth0-secret", body),
    )


def test_auth0_invalid_signature() -> None:
    """Wrong HMAC is rejected without leaking the secret."""
    with pytest.raises(UnauthorizedError) as exc_info:
        Auth0Client(settings=_settings()).verify_webhook_signature(
            body=b"{}",
            signature="deadbeef",
        )
    assert exc_info.value.code == "INVALID_WEBHOOK_SIGNATURE"


def test_auth0_missing_secret() -> None:
    """Unconfigured Auth0 webhooks return WEBHOOK_NOT_CONFIGURED."""
    with pytest.raises(AppError) as exc_info:
        Auth0Client(settings=_settings(auth0_webhook_secret="")).verify_webhook_signature(
            body=b"{}",
            signature="abc",
        )
    assert exc_info.value.code == "WEBHOOK_NOT_CONFIGURED"


def test_billing_valid_signature() -> None:
    """Billing HMAC is accepted."""
    body = b'{"type":"customer.subscription.deleted"}'
    BillingClient(settings=_settings()).verify_webhook_signature(
        body=body,
        signature=_sign("billing-secret", body),
    )
