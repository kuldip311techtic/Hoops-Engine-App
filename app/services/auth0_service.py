"""Auth0 webhook use-case."""

import json

from loguru import logger

from app.clients.auth0_client import Auth0Client
from app.exceptions.base import UnauthorizedError
from app.models.user import UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.webhook import Auth0WebhookPayload


class Auth0Service:
    """Handles Auth0 event callbacks after signature verification."""

    def __init__(
        self,
        client: Auth0Client,
        users: UserRepository,
    ) -> None:
        """Inject the Auth0 adapter and user repository."""
        self._client = client
        self._users = users

    async def handle_webhook(self, raw_body: bytes, signature_header: str) -> dict:
        """Verify HMAC and apply the event.

        Unknown events are acknowledged. ``user.blocked`` deactivates the user.
        """
        if not self._client.verify_webhook_signature(raw_body, signature_header):
            raise UnauthorizedError("Invalid signature", code="INVALID_SIGNATURE")
        payload = Auth0WebhookPayload.model_validate(json.loads(raw_body.decode("utf-8")))
        logger.info(
            "auth0_webhook event={} domain={}",
            payload.event,
            self._client.domain(),
        )
        if payload.event == "user.blocked" and payload.user_email:
            user = await self._users.get_by_email(payload.user_email)
            if user is not None and user.role != UserRole.SUPER_ADMIN:
                user.is_active = False
        return {"accepted": True, "event": payload.event}
