"""Billing webhook HMAC verification. Routes must not implement this inline."""

import hashlib
import hmac

from app.core.config import Settings, get_settings
from app.exceptions.base import UnauthorizedError


class BillingClient:
    """Verifies billing provider webhook signatures."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Bind application settings."""
        self._settings = settings or get_settings()

    def verify_webhook_signature(self, raw_body: bytes, signature_header: str) -> bool:
        """Return True when ``signature_header`` matches HMAC-SHA256 of ``raw_body``.

        Raises:
            UnauthorizedError: If BILLING_WEBHOOK_SECRET is not configured.
        """
        secret = self._settings.billing_webhook_secret
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
