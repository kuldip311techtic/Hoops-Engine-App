"""Auth middleware helpers."""

import pytest

from app.core.security import create_access_token, create_refresh_token, decode_token
from app.exceptions.base import UnauthorizedError
from app.middleware.auth import is_public_path, refresh_access_token


def test_public_paths() -> None:
    """Health, docs, and login are public."""
    assert is_public_path("/api/v1/health") is True
    assert is_public_path("/api/v1/health/ready") is True
    assert is_public_path("/docs") is True
    assert is_public_path("/api/v1/auth/login") is True
    assert is_public_path("/api/auth/login") is True
    assert is_public_path("/api/v1/auth/change-password") is False


def test_refresh_access_token_issues_new_access_token() -> None:
    """A refresh token yields a new access token."""
    refresh = create_refresh_token("abc", token_version=2)
    access = refresh_access_token(refresh)
    payload = decode_token(access)
    assert payload["sub"] == "abc"
    assert payload["type"] == "access"
    assert payload["ver"] == 2


def test_refresh_rejects_access_token() -> None:
    """Access tokens cannot be used in the refresh helper."""
    access = create_access_token("abc")
    with pytest.raises(UnauthorizedError):
        refresh_access_token(access)


def test_refresh_rejects_garbage() -> None:
    """Malformed tokens are rejected."""
    with pytest.raises(UnauthorizedError):
        refresh_access_token("nope")
