"""Billing provider adapter (Stripe-compatible env, no SDK in routes)."""

import hashlib
import hmac

from app.core.config import Settings, get_settings
from app.exceptions import AppError, UnauthorizedError


class BillingClient:
    """Webhook signature verification and env for the billing provider.

    Subscription state is persisted locally. Stripe (or another vendor) is not
    called from this adapter unless credentials exist for webhook verification.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def webhook_secret(self) -> str:
        """Prefer BILLING_WEBHOOK_SECRET, then STRIPE_WEBHOOK_SECRET."""
        return self._settings.billing_webhook_secret or self._settings.stripe_webhook_secret

    def verify_webhook_signature(self, *, body: bytes, signature: str | None) -> None:
        """Validate a billing webhook HMAC.

        Raises:
            AppError: Secret is not configured.
            UnauthorizedError: Signature missing or invalid.
        """
        secret = self.webhook_secret()
        if not secret:
            raise AppError(
                "Billing webhooks are not configured",
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
