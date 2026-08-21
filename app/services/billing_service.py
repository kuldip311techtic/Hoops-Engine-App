"""Billing webhook use-case and subscription access updates."""

import json
from datetime import datetime, timezone

from loguru import logger

from app.clients.billing_client import BillingClient
from app.exceptions.base import NotFoundError, UnauthorizedError
from app.models.subscription import SubscriptionStatus
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.webhook import BillingWebhookPayload


class BillingService:
    """Applies billing events to the subscriptions table."""

    def __init__(
        self,
        client: BillingClient,
        users: UserRepository,
        subscriptions: SubscriptionRepository,
    ) -> None:
        """Inject billing adapter and repositories."""
        self._client = client
        self._users = users
        self._subscriptions = subscriptions

    async def handle_webhook(self, raw_body: bytes, signature_header: str) -> dict:
        """Verify HMAC and upsert the user's subscription."""
        if not self._client.verify_webhook_signature(raw_body, signature_header):
            raise UnauthorizedError("Invalid signature", code="INVALID_SIGNATURE")
        payload = BillingWebhookPayload.model_validate(
            json.loads(raw_body.decode("utf-8"))
        )
        user = await self._users.get_by_email(payload.user_email)
        if user is None:
            raise NotFoundError("User not found", code="USER_NOT_FOUND")
        try:
            status = SubscriptionStatus(payload.status.upper())
        except ValueError:
            status = SubscriptionStatus.EXPIRED
        cancelled_at = None
        if status == SubscriptionStatus.CANCELLED:
            cancelled_at = datetime.now(timezone.utc)
        await self._subscriptions.upsert(
            user_id=user.id,
            status=status,
            current_period_end=payload.current_period_end,
            cancelled_at=cancelled_at,
        )
        logger.info("billing_webhook user_id={} status={}", user.id, status.value)
        return {"accepted": True, "status": status.value}
