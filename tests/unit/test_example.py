"""Unit tests for JWT and password helpers."""

import pytest
from jose import JWTError

from app.core.security import (
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_password() -> None:
    """Hashed passwords verify; a wrong password does not."""
    hashed = hash_password("Securepass1!")
    assert hashed != "Securepass1!"
    assert verify_password("Securepass1!", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_create_and_decode_access_token() -> None:
    """Access tokens round-trip subject and version claims."""
    token = create_access_token("user-1", token_version=3)
    payload = decode_token(token)
    assert payload["sub"] == "user-1"
    assert payload["type"] == TOKEN_TYPE_ACCESS
    assert payload["ver"] == 3


def test_decode_token_invalid_raises() -> None:
    """Garbage tokens raise JWTError."""
    with pytest.raises(JWTError):
        decode_token("not-a-jwt")


def test_refresh_token_type_claim() -> None:
    """Refresh tokens are tagged with type=refresh."""
    token = create_refresh_token("user-1", token_version=1)
    payload = decode_token(token)
    assert payload["type"] == TOKEN_TYPE_REFRESH


def test_settings_load() -> None:
    """Settings load JWT algorithm from environment."""
    from app.core.config import get_settings

    assert get_settings().jwt_algorithm == "HS256"
