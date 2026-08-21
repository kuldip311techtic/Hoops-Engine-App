"""Webhook routes. Signature verification happens in client/service layers."""

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.auth0_client import Auth0Client
from app.clients.billing_client import BillingClient
from app.dependencies.db import get_db
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.common import SuccessResponse, openapi_error_map
from app.schemas.webhook import Auth0WebhookPayload, BillingWebhookPayload
from app.services.auth0_service import Auth0Service
from app.services.billing_service import BillingService

router = APIRouter()
_errors = openapi_error_map()


def get_auth0_service(db: AsyncSession = Depends(get_db)) -> Auth0Service:
    """Build Auth0Service for this request."""
    return Auth0Service(Auth0Client(), UserRepository(db))


def get_billing_service(db: AsyncSession = Depends(get_db)) -> BillingService:
    """Build BillingService for this request."""
    return BillingService(
        BillingClient(),
        UserRepository(db),
        SubscriptionRepository(db),
    )


@router.post(
    "/webhooks/auth0",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Auth0 event webhook",
    description=(
        "Receives Auth0 callbacks. The raw body is HMAC-SHA256 verified with "
        "AUTH0_WEBHOOK_SECRET using header `X-Auth0-Signature`. Sandbox vs "
        "production domain selection is handled inside Auth0Client. Pass a "
        "JSON body matching Auth0WebhookPayload so Swagger documents `event`, "
        "`user_email`, and `environment`."
    ),
    tags=["webhooks"],
    responses={
        200: {"description": "Event accepted"},
        401: _errors[401],
        422: _errors[422],
        500: _errors[500],
    },
)
async def auth0_webhook(
    payload: Auth0WebhookPayload,
    request: Request,
    x_auth0_signature: str = Header(
        ...,
        alias="X-Auth0-Signature",
        description="HMAC-SHA256 hex digest of the raw body",
    ),
    service: Auth0Service = Depends(get_auth0_service),
) -> dict:
    """Accept an Auth0 webhook after HMAC verification."""
    raw = await request.body()
    data = await service.handle_webhook(raw, x_auth0_signature)
    return {"success": True, "message": "Webhook accepted", "data": data}


@router.post(
    "/webhooks/billing",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Billing subscription webhook",
    description=(
        "Receives subscription lifecycle events. Verified with "
        "BILLING_WEBHOOK_SECRET via `X-Billing-Signature`. Cancelled "
        "subscriptions retain access until `current_period_end`. Super Admins "
        "are never billed."
    ),
    tags=["webhooks"],
    responses={
        200: {"description": "Subscription updated"},
        401: _errors[401],
        404: _errors[404],
        422: _errors[422],
        500: _errors[500],
    },
)
async def billing_webhook(
    payload: BillingWebhookPayload,
    request: Request,
    x_billing_signature: str = Header(
        ...,
        alias="X-Billing-Signature",
        description="HMAC-SHA256 hex digest of the raw body",
    ),
    service: BillingService = Depends(get_billing_service),
) -> dict:
    """Accept a billing webhook after HMAC verification."""
    raw = await request.body()
    data = await service.handle_webhook(raw, x_billing_signature)
    return {"success": True, "message": "Webhook accepted", "data": data}
