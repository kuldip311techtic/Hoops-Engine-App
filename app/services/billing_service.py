"""Billing / subscription access rules."""

from datetime import datetime, timezone

from app.exceptions import ForbiddenError
from app.models.subscription import Subscription
from app.repositories.subscription_repository import SubscriptionRepository
from app.schemas.auth import SubscriptionAccessData
from app.schemas.webhook import BillingWebhookRequest


class BillingService:
    """Decide whether an account still has product access after cancellation."""

    def __init__(self, repository: SubscriptionRepository) -> None:
        self._repository = repository

    def access_for_super_admin(self) -> SubscriptionAccessData:
        """Platform Super Admins are not billed; always allowed."""
        return SubscriptionAccessData(
            status="not_applicable",
            has_access=True,
            access_until=None,
        )

    def evaluate(self, subscription: Subscription | None) -> SubscriptionAccessData:
        """Map a stored subscription to an access snapshot."""
        if subscription is None:
            return SubscriptionAccessData(
                status="not_applicable",
                has_access=True,
                access_until=None,
            )
        access_until = subscription.access_until
        iso = access_until.isoformat() if access_until is not None else None
        now = datetime.now(timezone.utc)
        if subscription.status == "active":
            return SubscriptionAccessData(status="active", has_access=True, access_until=iso)
        if subscription.status == "cancelled":
            still_valid = access_until is None or access_until >= now
            if still_valid:
                return SubscriptionAccessData(
                    status="cancelled",
                    has_access=True,
                    access_until=iso,
                )
            return SubscriptionAccessData(
                status="expired",
                has_access=False,
                access_until=iso,
            )
        return SubscriptionAccessData(
            status=subscription.status,
            has_access=False,
            access_until=iso,
        )

    def ensure_access(self, snapshot: SubscriptionAccessData) -> None:
        """Raise if the account may not use the product."""
        if not snapshot.has_access:
            raise ForbiddenError(
                "Subscription has ended. Access is no longer available.",
                code="SUBSCRIPTION_EXPIRED",
            )

    async def access_for_email(self, email: str) -> SubscriptionAccessData:
        """Load subscription by email and evaluate access."""
        sub = await self._repository.get_by_email(email)
        return self.evaluate(sub)

    async def apply_cancellation(self, payload: BillingWebhookRequest) -> SubscriptionAccessData:
        """Record a cancellation that retains access until period end."""
        cancelled_at = datetime.now(timezone.utc)
        access_until = payload.access_until
        if access_until is not None and access_until.tzinfo is None:
            access_until = access_until.replace(tzinfo=timezone.utc)
        row = await self._repository.upsert_cancelled(
            email=str(payload.email),
            access_until=access_until,
            provider_ref=payload.provider_ref,
            cancelled_at=cancelled_at,
        )
        return self.evaluate(row)
