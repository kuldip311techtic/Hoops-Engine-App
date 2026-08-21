"""Auth0 adapter: sandbox vs production domain and webhook HMAC."""

import hashlib
import hmac

from app.core.config import Settings, get_settings
from app.exceptions.base import UnauthorizedError


class Auth0Client:
    """Encapsulates Auth0 configuration. Login does not call Auth0 APIs."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Bind application settings."""
        self._settings = settings or get_settings()

    def client_id(self) -> str:
        """Return AUTH0_CLIENT_ID from settings."""
        return self._settings.auth0_client_id

    def client_secret(self) -> str:
        """Return AUTH0_CLIENT_SECRET from settings. Do not log this value."""
        return self._settings.auth0_client_secret

    def domain(self) -> str:
        """Return the Auth0 domain for the current environment.

        Production uses AUTH0_DOMAIN. Other environments prefer
        AUTH0_SANDBOX_DOMAIN and fall back to AUTH0_DOMAIN.
        """
        if self._settings.is_production:
            return self._settings.auth0_domain
        return self._settings.auth0_sandbox_domain or self._settings.auth0_domain

    def verify_webhook_signature(self, raw_body: bytes, signature_header: str) -> bool:
        """Return True when ``signature_header`` matches HMAC-SHA256 of ``raw_body``.

        Raises:
            UnauthorizedError: If the webhook secret is not configured.
        """
        secret = self._settings.auth0_webhook_secret
        if not secret:
            raise UnauthorizedError(
                "Webhook is not configured",
                code="WEBHOOK_NOT_CONFIGURED",
            )
        expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        provided = signature_header.strip()
        if provided.lower().startswith("sha256="):
            provided = provided.split("=", 1)[1]
        return hmac.compare_digest(expected, provided)
