"""Auth0 application service wrapping ``Auth0Client``."""

from typing import Any

from loguru import logger

from app.clients.auth0_client import Auth0Client
from app.core.config import Settings, get_settings
from app.schemas.webhook import Auth0WebhookRequest


class Auth0Service:
    """Auth0 webhooks and environment handling. Not used for JWT password login."""

    def __init__(
        self,
        client: Auth0Client | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._client = client or Auth0Client(self._settings)

    def verify_webhook(self, *, body: bytes, signature: str | None) -> None:
        """Verify Auth0 webhook authenticity."""
        self._client.verify_webhook_signature(body=body, signature=signature)

    def handle_event(self, payload: Auth0WebhookRequest) -> dict[str, Any]:
        """Process an Auth0 event without leaking tenant details.

        Password-change events are informational here; session revocation for
        Super Admin is driven by ``token_version`` on change-password.
        """
        logger.info(
            "auth0_webhook_event type={} env={}",
            payload.type,
            self._client.runtime_environment(),
        )
        return {
            "type": payload.type,
            "email": str(payload.email) if payload.email else None,
            "description": payload.description,
            "environment": self._client.runtime_environment(),
        }
