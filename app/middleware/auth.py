"""Bearer authentication middleware and refresh-token helper."""

from jose import JWTError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.security import (
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH,
    create_access_token,
    decode_token,
)
from app.exceptions.base import UnauthorizedError
from app.schemas.common import error_body

PUBLIC_PATH_PREFIXES: tuple[str, ...] = (
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/health",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/api/auth/login",
    "/api/v1/webhooks",
)


def is_public_path(path: str) -> bool:
    """Return True when ``path`` does not require a Bearer token."""
    if path.rstrip("/") == "/api/v1/health" or path.startswith("/api/v1/health"):
        return True
    return any(path == prefix or path.startswith(prefix + "/") or path.startswith(prefix)
               for prefix in PUBLIC_PATH_PREFIXES)


def refresh_access_token(refresh_token: str) -> str:
    """Issue a new access token from a valid refresh token.

    This is the refresh-flow helper required by the project scaffold.
    Session revocation (token_version) is enforced by AuthService.refresh.
    """
    try:
        payload = decode_token(refresh_token)
    except JWTError as exc:
        raise UnauthorizedError("Invalid refresh token") from exc
    if payload.get("type") != TOKEN_TYPE_REFRESH:
        raise UnauthorizedError("Invalid refresh token")
    subject = payload.get("sub")
    if not subject:
        raise UnauthorizedError("Invalid refresh token")
    version = int(payload.get("ver", 1))
    return create_access_token(subject, token_version=version)


class AuthMiddleware(BaseHTTPMiddleware):
    """Reject protected routes that lack a valid access JWT."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """Allow public paths; otherwise require a valid Bearer access token."""
        if request.method == "OPTIONS" or is_public_path(request.url.path):
            return await call_next(request)
        header = request.headers.get("authorization") or request.headers.get(
            "Authorization"
        )
        if not header or not header.lower().startswith("bearer "):
            return JSONResponse(
                status_code=401,
                content=error_body("Not authenticated", "UNAUTHORIZED"),
            )
        token = header.split(" ", 1)[1].strip()
        try:
            payload = decode_token(token)
        except JWTError:
            return JSONResponse(
                status_code=401,
                content=error_body("Not authenticated", "UNAUTHORIZED"),
            )
        if payload.get("type") != TOKEN_TYPE_ACCESS:
            return JSONResponse(
                status_code=401,
                content=error_body("Not authenticated", "UNAUTHORIZED"),
            )
        request.state.token_payload = payload
        return await call_next(request)
