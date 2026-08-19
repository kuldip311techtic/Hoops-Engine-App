"""Unit tests for security utilities."""

from datetime import timedelta

import pytest

from app.core.config import get_settings
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    """Clear settings cache before each test."""
    get_settings.cache_clear()


def test_create_access_token_returns_decodable_jwt() -> None:
    """Access tokens should encode and decode with expected claims."""
    token = create_access_token(
        subject="user-123",
        claims={"role": "super_admin"},
    )
    payload = decode_access_token(token)
    assert payload["sub"] == "user-123"
    assert payload["role"] == "super_admin"
    assert "exp" in payload


def test_decode_access_token_invalid_signature_raises() -> None:
    """Tampered tokens should raise InvalidTokenError."""
    token = create_access_token(subject="user-123")
    tampered = token[:-4] + "xxxx"
    with pytest.raises(InvalidTokenError):
        decode_access_token(tampered)


def test_hash_password_and_verify_success() -> None:
    """Password hashing and verification should round-trip."""
    hashed = hash_password("SecurePass123!")
    assert verify_password("SecurePass123!", hashed) is True


def test_verify_password_wrong_password_returns_false() -> None:
    """Wrong passwords should not verify."""
    hashed = hash_password("SecurePass123!")
    assert verify_password("WrongPassword!", hashed) is False


def test_create_access_token_respects_custom_expiry() -> None:
    """Custom expiry deltas should be reflected in token lifetime."""
    token = create_access_token(
        subject="user-123",
        expires_delta=timedelta(minutes=5),
    )
    payload = decode_access_token(token)
    settings = get_settings()
    expected_max_seconds = 5 * 60 + 5
    lifetime = payload["exp"] - payload["iat"]
    assert lifetime <= expected_max_seconds
    assert lifetime > 0
    assert settings.access_token_expire_minutes == 30
