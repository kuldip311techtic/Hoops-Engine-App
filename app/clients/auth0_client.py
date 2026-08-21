"""Auth0 SDK/HTTP adapter. Routes must never import Auth0 or call the tenant API."""

import hashlib
import hmac
from typing import Any

from app.core.config import Settings, get_settings
from app.exceptions import AppError, UnauthorizedError


class Auth0Client:
    """Auth0 configuration, environment, and webhook signature verification.

    Super Admin password login uses local OAuth2/JWT (AUTH_STRATEGY=jwt). This
    client exists so Auth0 webhooks and a future Auth0 grant can share one
    adapter. It does not perform Resource Owner Password Grant.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def is_configured(self) -> bool:
        """Return True when tenant credentials are present."""
        return self._settings.auth0_is_configured

    def runtime_environment(self) -> str:
        """Return ``sandbox`` or ``production`` for Auth0."""
        return self._settings.auth0_runtime

    def verify_webhook_signature(self, *, body: bytes, signature: str | None) -> None:
        """Validate an Auth0 webhook HMAC.

        Raises:
            AppError: Secret is not configured.
            UnauthorizedError: Signature missing or invalid.
        """
        secret = self._settings.auth0_webhook_secret
        if not secret:
            raise AppError(
                "Auth0 webhooks are not configured",
                status_code=503,
                code="WEBHOOK_NOT_CONFIGURED",
            )
        if not signature:
            raise UnauthorizedError(
                "Invalid webhook signature",
                code="INVALID_WEBHOOK_SIGNATURE",
            )
        expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        provided = signature.split("=")[-1].strip()
        if not hmac.compare_digest(expected, provided):
            raise UnauthorizedError(
                "Invalid webhook signature",
                code="INVALID_WEBHOOK_SIGNATURE",
            )

    def sandbox_vs_production(self) -> dict[str, Any]:
        """Return a UI-safe snapshot of Auth0 environment (no secrets)."""
        return {
            "configured": self.is_configured(),
            "environment": self.runtime_environment(),
            "domain_set": bool(self._settings.auth0_domain),
        }
