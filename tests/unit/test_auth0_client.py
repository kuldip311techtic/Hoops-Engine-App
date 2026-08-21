"""Auth0Client unit tests."""

import hashlib
import hmac

import pytest

from app.clients.auth0_client import Auth0Client
from app.core.config import Settings
from app.exceptions.base import UnauthorizedError


def _sign(secret: str, body: bytes) -> str:
    """HMAC-SHA256 hex digest."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_auth0_valid_signature() -> None:
    """Matching HMAC is accepted."""
    settings = Settings(
        auth0_webhook_secret="s3cret",
        jwt_secret_key="x",
    )
    client = Auth0Client(settings)
    body = b'{"event":"ping"}'
    assert client.verify_webhook_signature(body, _sign("s3cret", body)) is True


def test_auth0_invalid_signature() -> None:
    """Mismatched HMAC is rejected."""
    settings = Settings(auth0_webhook_secret="s3cret", jwt_secret_key="x")
    client = Auth0Client(settings)
    assert client.verify_webhook_signature(b"{}", "deadbeef") is False


def test_auth0_missing_secret() -> None:
    """Unconfigured secret raises UnauthorizedError."""
    client = Auth0Client(Settings(auth0_webhook_secret="", jwt_secret_key="x"))
    with pytest.raises(UnauthorizedError) as exc:
        client.verify_webhook_signature(b"{}", "abc")
    assert exc.value.code == "WEBHOOK_NOT_CONFIGURED"


def test_auth0_sandbox_vs_production() -> None:
    """Production uses AUTH0_DOMAIN; other envs prefer the sandbox domain."""
    prod = Auth0Client(
        Settings(
            environment="production",
            auth0_domain="prod.example.auth0.com",
            auth0_sandbox_domain="sandbox.example.auth0.com",
            jwt_secret_key="x",
        )
    )
    sandbox = Auth0Client(
        Settings(
            environment="development",
            auth0_domain="prod.example.auth0.com",
            auth0_sandbox_domain="sandbox.example.auth0.com",
            jwt_secret_key="x",
        )
    )
    assert prod.domain() == "prod.example.auth0.com"
    assert sandbox.domain() == "sandbox.example.auth0.com"
    assert prod.client_id() == ""
    settings = Settings(
        auth0_client_id="cid",
        auth0_client_secret="csecret",
        jwt_secret_key="x",
    )
    creds = Auth0Client(settings)
    assert creds.client_id() == "cid"
    assert creds.client_secret() == "csecret"
