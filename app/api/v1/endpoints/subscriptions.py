```python
"""Admin subscription plan routes. Thin: validate DTO, call service, wrap envelope."

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.dependencies.admin import (
    get_current_super_admin,
    get_subscription_plan_service,
)
from app.models.user import User
from app.schemas.common import AdminSuccessResponse, openapi_error_map
from app.schemas.subscription_plan import (
    SubscriptionPlanCreateRequest,
    SubscriptionPlanListResponse,
    SubscriptionPlanUpdateRequest,
)
from app.services.subscription_plan_service import SubscriptionPlanService

router = APIRouter()
_errors = openapi_error_map()

_plan_example = {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Pro Coach",
    "description": "Full access for coaching teams.",
    "price": "29.99",
    "billing_cycle": "Monthly",
    "is_published": True,
    "created_at": "2026-08-21T12:00:00+00:00",
    "updated_at": "2026-08-21T12:00:00+00:00",
}

_common_responses = {
    400: _errors[400],
    401: _errors[401],
    403: _errors[403],
    404: _errors[404],
    409: _errors[409],
    422: _errors[422],
    500: _errors[500],
}

@router.get(
    "",
    response_model=SubscriptionPlanListResponse,
    status_code=status.HTTP_200_OK,
    operation_id="list_subscription_plans",
    summary="List subscription plans",
    description=(
        "Super Admin only. Returns subscription plans from the catalog. By default "
        "all plans are returned (published and unpublished) so the admin UI can "
        "manage the full catalog. Set query parameter `published_only=true` to "
        "return only published plans — the same filter end users receive. "
        "Requires `Authorization: Bearer <access_token>` for a Super Admin account."
    ),
    tags=["admin"],
    responses={
        200: {
            "description": "Plans retrieved.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Subscription plans retrieved",
                        "description": "Subscription plans retrieved successfully.",
                        "data": {
                            "items": [_plan_example],
                        },
                    }
                }
            },
        },
        **_common_responses,
    },
)
async def list_subscription_plans(
    published_only: bool = Query(
        default=False,
        description=(
            "When true, return only published plans (end-user visibility filter)."
        ),
    ),
    _admin: User = Depends(get_current_super_admin),
    service: SubscriptionPlanService = Depends(get_subscription_plan_service),
) -> dict:
    """Return subscription plans for the Super Admin catalog screen."""
    items = await service.list_plans(published_only=published_only)
    return {
        "success": True,
        "message": "Subscription plans retrieved",
        "description": "Subscription plans retrieved successfully.",
        "data": {
            "items": [item.model_dump(mode="json") for item in items],
        },
    }
```