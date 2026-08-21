"""Authentication middleware and refresh-token flow.

Token cryptography lives in ``app.core.security``. This module only extracts
Bearer credentials, attaches decoded claims to ``request.state``, and issues a
new access token from a valid refresh token.
"""

from jose import JWTError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.security import (
    create_access_token,
    decode_access_token,
    decode_refresh_token,
)
from app.exceptions import UnauthorizedError

PUBLIC_PATH_PREFIXES = (
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/health",
    "/api/health",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/auth/login",
    "/api/auth/refresh",
    "/api/v1/webhooks",
)


def extract_bearer_token(request: Request) -> str | None:
    """Return the Bearer token from the Authorization header, if present."""
    header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not header:
        return None
    scheme, _, value = header.partition(" ")
    if scheme.lower() != "bearer" or not value:
        return None
    return value.strip()


def is_public_path(path: str) -> bool:
    """Return True if ``path`` does not require authentication."""
    return any(path == prefix or path.startswith(prefix + "/") for prefix in PUBLIC_PATH_PREFIXES)


def refresh_access_token(refresh_token: str) -> str:
    """Issue a new access token from a valid refresh token.

    Raises:
        UnauthorizedError: If the refresh token is missing, expired, or not type=refresh.
    """
    try:
        payload = decode_refresh_token(refresh_token)
    except JWTError as exc:
        raise UnauthorizedError(
            "Invalid or expired refresh token",
            code="INVALID_REFRESH_TOKEN",
        ) from exc
    subject = payload.get("sub")
    if not subject:
        raise UnauthorizedError(
            "Invalid or expired refresh token",
            code="INVALID_REFRESH_TOKEN",
        )
    extra = {
        key: value
        for key, value in payload.items()
        if key not in {"sub", "iat", "exp", "type"}
    }
    return create_access_token(subject=str(subject), extra_claims=extra)


class AuthMiddleware(BaseHTTPMiddleware):
    """Optionally decode a Bearer access token onto ``request.state.token_payload``.

    Public routes are never rejected. Protected routes still use FastAPI
    ``Depends(get_current_super_admin)``; this middleware only hydrates state
    so downstream code can read claims without re-decoding.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        """Attach decoded JWT claims when a Bearer token is present."""
        request.state.token_payload = None
        token = extract_bearer_token(request)
        if token:
            try:
                request.state.token_payload = decode_access_token(token)
            except JWTError:
                request.state.token_payload = None
                if not is_public_path(request.url.path):
                    # Invalid token on a protected path is left to the dependency
                    # so OpenAPI/error envelope stay consistent.
                    pass
        return await call_next(request)
