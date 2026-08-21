"""Unit tests for JWT and password helpers (setup-ticket example module)."""

import pytest
from jose import JWTError

from app.core.security import (
    ACCESS_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_password() -> None:
    """Hashed passwords verify; wrong plaintext does not."""
    hashed = hash_password("CorrectHorse1!")
    assert hashed != "CorrectHorse1!"
    assert verify_password("CorrectHorse1!", hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_create_and_decode_access_token() -> None:
    """Access tokens include sub, type=access, and extra claims."""
    token = create_access_token("admin-id", extra_claims={"role": "super_admin"})
    payload = decode_access_token(token)
    assert payload["sub"] == "admin-id"
    assert payload["type"] == ACCESS_TOKEN_TYPE
    assert payload["role"] == "super_admin"
    assert "exp" in payload
    assert "iat" in payload


def test_refresh_token_type_claim() -> None:
    """Refresh tokens are distinct from access tokens."""
    token = create_refresh_token("admin-id")
    payload = decode_refresh_token(token)
    assert payload["type"] == REFRESH_TOKEN_TYPE
    with pytest.raises(JWTError):
        decode_access_token(token)


def test_decode_token_invalid_raises() -> None:
    """Malformed tokens raise JWTError."""
    with pytest.raises(JWTError):
        decode_token("not-a-jwt")
