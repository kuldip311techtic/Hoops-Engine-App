"""Admin subscription plan routes. Thin: validate DTO, call service, wrap envelope."""

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


@router.post(
    "",
    response_model=AdminSuccessResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_subscription_plan",
    summary="Create a subscription plan",
    description=(
        "Super Admin only. Creates a subscription plan with `name`, `price`, and "
        "`billing_cycle`. Optional `description` and `is_published` may be supplied. "
        "Duplicate names return 409 SUBSCRIPTION_PLAN_ALREADY_EXISTS. Requires "
        "Bearer token for Super Admin."
    ),
    tags=["admin"],
    responses={
        201: {
            "description": "Plan created.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Subscription plan created",
                        "description": "The subscription plan was added successfully.",
                        "data": _plan_example,
                    }
                }
            },
        },
        **_common_responses,
    },
)
async def create_subscription_plan(
    body: SubscriptionPlanCreateRequest,
    _admin: User = Depends(get_current_super_admin),
    service: SubscriptionPlanService = Depends(get_subscription_plan_service),
) -> dict:
    """Add a subscription plan to the catalog."""
    plan = await service.create_plan(
        name=body.name,
        description=body.description,
        price=body.price,
        billing_cycle=body.billing_cycle,
        is_published=body.is_published,
    )
    return {
        "success": True,
        "message": "Subscription plan created",
        "description": "The subscription plan was added successfully.",
        "data": plan.model_dump(mode="json"),
    }


@router.get(
    "/{plan_id}",
    response_model=AdminSuccessResponse,
    status_code=status.HTTP_200_OK,
    operation_id="get_subscription_plan",
    summary="Get a subscription plan",
    description=(
        "Super Admin only. Returns a single subscription plan by id. Unknown ids "
        "return 404 SUBSCRIPTION_PLAN_NOT_FOUND."
    ),
    tags=["admin"],
    responses={
        200: {
            "description": "Plan retrieved.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Subscription plan retrieved",
                        "description": "Subscription plan retrieved successfully.",
                        "data": _plan_example,
                    }
                }
            },
        },
        **_common_responses,
    },
)
async def get_subscription_plan(
    plan_id: UUID,
    _admin: User = Depends(get_current_super_admin),
    service: SubscriptionPlanService = Depends(get_subscription_plan_service),
) -> dict:
    """Return one subscription plan."""
    plan = await service.get_plan(plan_id)
    return {
        "success": True,
        "message": "Subscription plan retrieved",
        "description": "Subscription plan retrieved successfully.",
        "data": plan.model_dump(mode="json"),
    }


@router.put(
    "/{plan_id}",
    response_model=AdminSuccessResponse,
    status_code=status.HTTP_200_OK,
    operation_id="update_subscription_plan",
    summary="Update a subscription plan",
    description=(
        "Super Admin only. Partially updates a subscription plan. All body fields are "
        "optional. Renaming to an existing plan name returns 409 "
        "SUBSCRIPTION_PLAN_ALREADY_EXISTS. Unknown ids return 404."
    ),
    tags=["admin"],
    responses={
        200: {
            "description": "Plan updated.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Subscription plan updated",
                        "description": "The subscription plan was updated successfully.",
                        "data": _plan_example,
                    }
                }
            },
        },
        **_common_responses,
    },
)
async def update_subscription_plan(
    plan_id: UUID,
    body: SubscriptionPlanUpdateRequest,
    _admin: User = Depends(get_current_super_admin),
    service: SubscriptionPlanService = Depends(get_subscription_plan_service),
) -> dict:
    """Edit an existing subscription plan."""
    plan = await service.update_plan(
        plan_id,
        name=body.name,
        description=body.description,
        price=body.price,
        billing_cycle=body.billing_cycle,
        is_published=body.is_published,
    )
    return {
        "success": True,
        "message": "Subscription plan updated",
        "description": "The subscription plan was updated successfully.",
        "data": plan.model_dump(mode="json"),
    }


@router.delete(
    "/{plan_id}",
    response_model=AdminSuccessResponse,
    status_code=status.HTTP_200_OK,
    operation_id="delete_subscription_plan",
    summary="Remove a subscription plan",
    description=(
        "Super Admin only. Soft-removes a plan by setting `is_published` to false. "
        "Unknown ids return 404 SUBSCRIPTION_PLAN_NOT_FOUND."
    ),
    tags=["admin"],
    responses={
        200: {
            "description": "Plan removed.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Subscription plan removed",
                        "description": "The subscription plan was removed successfully.",
                        "data": {**_plan_example, "is_published": False},
                    }
                }
            },
        },
        **_common_responses,
    },
)
async def delete_subscription_plan(
    plan_id: UUID,
    _admin: User = Depends(get_current_super_admin),
    service: SubscriptionPlanService = Depends(get_subscription_plan_service),
) -> dict:
    """Remove a subscription plan from the published catalog."""
    plan = await service.remove_plan(plan_id)
    return {
        "success": True,
        "message": "Subscription plan removed",
        "description": "The subscription plan was removed successfully.",
        "data": plan.model_dump(mode="json"),
    }