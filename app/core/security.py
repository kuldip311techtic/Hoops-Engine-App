"""Password hashing and JWT helpers for the OAuth2 bearer flow."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Return True when ``plain_password`` matches ``password_hash``."""
    return pwd_context.verify(plain_password, password_hash)


def _encode(claims: dict[str, Any], expires_delta: timedelta) -> str:
    """Encode a JWT with an expiration claim using application settings."""
    settings = get_settings()
    payload = dict(claims)
    payload["exp"] = datetime.now(UTC) + expires_delta
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_access_token(
    subject: UUID | str,
    token_version: int = 1,
    extra: dict[str, Any] | None = None,
) -> str:
    """Create a signed access token for ``subject``."""
    settings = get_settings()
    claims: dict[str, Any] = {
        "sub": str(subject),
        "type": TOKEN_TYPE_ACCESS,
        "ver": token_version,
    }
    if extra:
        claims.update(extra)
    return _encode(
        claims,
        timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(subject: UUID | str, token_version: int = 1) -> str:
    """Create a signed refresh token for ``subject``."""
    settings = get_settings()
    claims: dict[str, Any] = {
        "sub": str(subject),
        "type": TOKEN_TYPE_REFRESH,
        "ver": token_version,
    }
    return _encode(claims, timedelta(days=settings.refresh_token_expire_days))


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT.

    Raises:
        JWTError: If the token is expired, malformed, or has a bad signature.
    """
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        raise
