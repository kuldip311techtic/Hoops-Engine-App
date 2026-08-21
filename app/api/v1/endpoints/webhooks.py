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
_public = {"security": []}


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
    operation_id="auth0_webhook",
    summary="Auth0 event webhook",
    description=(
        "Public Auth0 callback. No Bearer token. The JSON body is documented as "
        "`Auth0WebhookPayload` (`event`, optional `user_email`, optional "
        "`environment`) so Swagger shows every field. The raw body is also read "
        "for HMAC-SHA256 verification against AUTH0_WEBHOOK_SECRET using header "
        "`X-Auth0-Signature` (hex digest, optional `sha256=` prefix). "
        "Unknown events are acknowledged. `user.blocked` deactivates a matching "
        "non-Super-Admin user. Invalid signatures return 401 INVALID_SIGNATURE. "
        "Login itself is local OAuth2/JWT; this webhook does not issue tokens."
    ),
    tags=["webhooks"],
    openapi_extra=_public,
    responses={
        200: {
            "description": "Event accepted.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Webhook accepted",
                        "data": {"accepted": True, "event": "user.blocked"},
                    }
                }
            },
        },
        400: _errors[400],
        401: {
            "description": "HMAC signature missing or invalid.",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Invalid signature",
                        "description": "Invalid signature",
                        "error": {"code": "INVALID_SIGNATURE", "details": None},
                    }
                }
            },
        },
        403: _errors[403],
        404: _errors[404],
        409: _errors[409],
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
        description="HMAC-SHA256 hex digest of the raw body (AUTH0_WEBHOOK_SECRET).",
        examples=["a1b2c3d4e5f678901234567890abcdefa1b2c3d4e5f678901234567890abcdef"],
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
    operation_id="billing_webhook",
    summary="Billing subscription webhook",
    description=(
        "Public billing callback. No Bearer token. JSON body is "
        "`BillingWebhookPayload`: `user_email`, `status` (ACTIVE, CANCELLED, "
        "EXPIRED), and `current_period_end`. Verified with BILLING_WEBHOOK_SECRET "
        "via `X-Billing-Signature`. Cancelled subscriptions retain product access "
        "until `current_period_end`. Super Admins are never billed. Unknown "
        "`user_email` returns 404 USER_NOT_FOUND. Bad HMAC returns 401 "
        "INVALID_SIGNATURE."
    ),
    tags=["webhooks"],
    openapi_extra=_public,
    responses={
        200: {
            "description": "Subscription upserted.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Webhook accepted",
                        "data": {"accepted": True, "status": "CANCELLED"},
                    }
                }
            },
        },
        400: _errors[400],
        401: {
            "description": "HMAC signature missing or invalid.",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Invalid signature",
                        "description": "Invalid signature",
                        "error": {"code": "INVALID_SIGNATURE", "details": None},
                    }
                }
            },
        },
        403: _errors[403],
        404: {
            "description": "No user exists for user_email.",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "User not found",
                        "description": "User not found",
                        "error": {"code": "USER_NOT_FOUND", "details": None},
                    }
                }
            },
        },
        409: _errors[409],
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
        description="HMAC-SHA256 hex digest of the raw body (BILLING_WEBHOOK_SECRET).",
        examples=["a1b2c3d4e5f678901234567890abcdefa1b2c3d4e5f678901234567890abcdef"],
    ),
    service: BillingService = Depends(get_billing_service),
) -> dict:
    """Accept a billing webhook after HMAC verification."""
    raw = await request.body()
    data = await service.handle_webhook(raw, x_billing_signature)
    return {"success": True, "message": "Webhook accepted", "data": data}
