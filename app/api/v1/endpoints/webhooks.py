"""Inbound Auth0 and billing webhooks."""

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.auth0_client import Auth0Client
from app.clients.billing_client import BillingClient
from app.dependencies.db import get_db
from app.repositories.subscription_repository import SubscriptionRepository
from app.schemas.common import ERROR_RESPONSES
from app.schemas.webhook import (
    Auth0WebhookRequest,
    BillingWebhookRequest,
    WebhookAckResponse,
)
from app.services.auth0_service import Auth0Service
from app.services.billing_service import BillingService
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

_WEBHOOK_ERRORS = {
    400: ERROR_RESPONSES[400],
    401: {
        "model": ERROR_RESPONSES[401]["model"],
        "description": "Missing or invalid X-Webhook-Signature HMAC",
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "message": "Invalid webhook signature",
                    "error": {
                        "code": "INVALID_WEBHOOK_SIGNATURE",
                        "details": None,
                    },
                }
            }
        },
    },
    403: ERROR_RESPONSES[403],
    404: ERROR_RESPONSES[404],
    409: ERROR_RESPONSES[409],
    422: ERROR_RESPONSES[422],
    500: ERROR_RESPONSES[500],
    503: {
        "model": ERROR_RESPONSES[503]["model"],
        "description": "Webhook secret is not configured",
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "message": "Auth0 webhooks are not configured",
                    "error": {
                        "code": "WEBHOOK_NOT_CONFIGURED",
                        "details": None,
                    },
                }
            }
        },
    },
}


def get_webhook_service(session: AsyncSession = Depends(get_db)) -> WebhookService:
    """Compose webhook handlers; vendor SDKs stay in clients."""
    return WebhookService(
        auth0_service=Auth0Service(client=Auth0Client()),
        billing_service=BillingService(SubscriptionRepository(session)),
        billing_client=BillingClient(),
    )


@router.post(
    "/auth0",
    response_model=WebhookAckResponse,
    status_code=status.HTTP_200_OK,
    summary="Auth0 event webhook",
    operation_id="auth0_event_webhook",
    description=(
        "Public callback for Auth0 events. Requires header "
        "``X-Webhook-Signature`` (hex HMAC-SHA256 of the raw body using "
        "AUTH0_WEBHOOK_SECRET). Sandbox vs production is selected via "
        "AUTH0_ENVIRONMENT or ENVIRONMENT. Does not authenticate dashboard "
        "users and is not used for Super Admin password login when "
        "AUTH_STRATEGY=jwt. Typed body: type, email, user_id, description."
    ),
    responses={
        200: {
            "model": WebhookAckResponse,
            "description": "Event accepted after HMAC verification",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Auth0 event accepted",
                        "data": {
                            "accepted": True,
                            "type": "scim.user.updated",
                            "email": "admin@example.com",
                            "description": "User password changed",
                            "message": "Auth0 event accepted",
                            "error": None,
                        },
                    }
                }
            },
        },
        **_WEBHOOK_ERRORS,
    },
)
async def auth0_webhook(
    request: Request,
    body: Auth0WebhookRequest,
    service: WebhookService = Depends(get_webhook_service),
    x_webhook_signature: str | None = Header(
        default=None,
        alias="X-Webhook-Signature",
        description=(
            "HMAC-SHA256 hex digest of the raw request body using "
            "AUTH0_WEBHOOK_SECRET. Optional in the signature for OpenAPI; "
            "missing values are rejected as 401 INVALID_WEBHOOK_SIGNATURE."
        ),
        examples=["3f9a0c1b2d4e5f67890123456789abcd"],
    ),
) -> WebhookAckResponse:
    """Accept an Auth0 event after signature verification."""
    raw = await request.body()
    return service.handle_auth0(body=raw, signature=x_webhook_signature, payload=body)


@router.post(
    "/billing",
    response_model=WebhookAckResponse,
    status_code=status.HTTP_200_OK,
    summary="Billing subscription webhook",
    operation_id="billing_subscription_webhook",
    description=(
        "Public callback for subscription cancellation. When a user cancels, "
        "access is retained until ``access_until`` (end of the billing cycle). "
        "Requires ``X-Webhook-Signature`` HMAC with BILLING_WEBHOOK_SECRET or "
        "STRIPE_WEBHOOK_SECRET. Body fields: type, email, access_until, "
        "description, provider_ref. Super Admin login is not gated on this row."
    ),
    responses={
        200: {
            "model": WebhookAckResponse,
            "description": "Cancellation recorded; access retained until period end",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Billing event accepted",
                        "data": {
                            "accepted": True,
                            "type": "customer.subscription.deleted",
                            "email": "coach@example.com",
                            "description": (
                                "Subscription cancelled; access retained "
                                "until the end of the billing cycle"
                            ),
                            "message": "Billing event accepted",
                            "error": None,
                        },
                    }
                }
            },
        },
        **_WEBHOOK_ERRORS,
    },
)
async def billing_webhook(
    request: Request,
    body: BillingWebhookRequest,
    service: WebhookService = Depends(get_webhook_service),
    x_webhook_signature: str | None = Header(
        default=None,
        alias="X-Webhook-Signature",
        description=(
            "HMAC-SHA256 hex digest of the raw request body using "
            "BILLING_WEBHOOK_SECRET or STRIPE_WEBHOOK_SECRET"
        ),
        examples=["3f9a0c1b2d4e5f67890123456789abcd"],
    ),
) -> WebhookAckResponse:
    """Record a subscription cancellation with retained access."""
    raw = await request.body()
    return await service.handle_billing(
        body=raw,
        signature=x_webhook_signature,
        payload=body,
    )
