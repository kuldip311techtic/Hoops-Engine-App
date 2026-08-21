"""Webhook orchestration for Auth0 and billing events."""

from app.clients.billing_client import BillingClient
from app.schemas.webhook import (
    Auth0WebhookRequest,
    BillingWebhookRequest,
    WebhookAckData,
    WebhookAckResponse,
)
from app.services.auth0_service import Auth0Service
from app.services.billing_service import BillingService


class WebhookService:
    """Verify signatures and dispatch webhook events."""

    def __init__(
        self,
        auth0_service: Auth0Service,
        billing_service: BillingService,
        billing_client: BillingClient,
    ) -> None:
        self._auth0_service = auth0_service
        self._billing_service = billing_service
        self._billing_client = billing_client

    def handle_auth0(
        self,
        *,
        body: bytes,
        signature: str | None,
        payload: Auth0WebhookRequest,
    ) -> WebhookAckResponse:
        """Verify and acknowledge an Auth0 webhook."""
        self._auth0_service.verify_webhook(body=body, signature=signature)
        handled = self._auth0_service.handle_event(payload)
        message = "Auth0 event accepted"
        return WebhookAckResponse(
            success=True,
            message=message,
            data=WebhookAckData(
                accepted=True,
                type=payload.type,
                email=handled.get("email") or "",
                description=payload.description or "",
                message=message,
                error=None,
                password="",
            ),
        )

    async def handle_billing(
        self,
        *,
        body: bytes,
        signature: str | None,
        payload: BillingWebhookRequest,
    ) -> WebhookAckResponse:
        """Verify and apply a billing subscription event."""
        self._billing_client.verify_webhook_signature(body=body, signature=signature)
        snapshot = await self._billing_service.apply_cancellation(payload)
        message = "Billing event accepted"
        description = payload.description or (
            "Subscription cancelled; access retained until the end of the billing cycle"
            if snapshot.has_access
            else "Subscription ended"
        )
        return WebhookAckResponse(
            success=True,
            message=message,
            data=WebhookAckData(
                accepted=True,
                type=payload.type,
                email=str(payload.email),
                description=description,
                message=message,
                error=None,
                password="",
            ),
        )
