# JWT Refresh Token Flow (Outline)

This document outlines the planned refresh token flow for Hoops Engine authentication.
Implementation is deferred to a future ticket; JAW-9404 establishes JWT utilities only.

## Current State (JAW-9404)

- `create_access_token()` issues short-lived JWT access tokens.
- `decode_access_token()` validates access tokens.
- Tokens are stateless; no server-side session store is required yet.

## Planned Refresh Flow

1. **Login** — Client receives:
   - `access_token` (short-lived, e.g. 30 minutes)
   - `refresh_token` (long-lived, e.g. 7 days; HttpOnly cookie or secure storage)

2. **Refresh** — `POST /api/v1/auth/refresh`
   - Accepts `refresh_token` in request body or HttpOnly cookie.
   - Validates signature, expiry, and revocation status.
   - Returns a new `access_token` and optionally rotates the `refresh_token`.

3. **Logout** — `POST /api/v1/auth/logout`
   - Invalidates the refresh token (Redis denylist or DB revocation table).
   - Client clears stored tokens.

## Security Considerations

- Refresh tokens must be stored securely (HttpOnly, Secure, SameSite cookies preferred).
- Rotate refresh tokens on each use to limit replay window.
- Maintain a revocation list for compromised tokens.
- Rate-limit refresh and login endpoints.

## Dependencies

- Redis or PostgreSQL table for refresh token storage/revocation (future).
- Additional Alembic migration for refresh token records (future).
