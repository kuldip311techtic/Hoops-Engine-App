"""Super Admin subscription plan management routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status

from app.dependencies.admin import get_current_super_admin, get_subscription_plan_service
from app.models.user import User
from app.schemas.common import openapi_error_map
from app.schemas.common import ErrorResponse
from app.schemas.subscription_plan import (
    SubscriptionPlanActionResponse,
    SubscriptionPlanCreateRequest,
    SubscriptionPlanListResponse,
    SubscriptionPlanUpdateRequest,
)
from app.services.subscription_plan_service import SubscriptionPlanService

router = APIRouter()
_errors = openapi_error_map()

_plan_example = {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Basic Plan",
    "description": "Entry tier for small organizations.",
    "price": "9.99",
    "billing_cycle": "monthly",
    "duration": "monthly",
    "status": "published",
    "is_published": True,
    "created_at": "2026-08-24T12:00:00+00:00",
    "updated_at": "2026-08-24T12:00:00+00:00",
}

_subscription_404 = {
    "description": "Subscription plan not found.",
    "content": {
        "application/json": {
            "example": {
                "success": False,
                "message": "Subscription plan not found",
                "description": "Subscription plan not found",
                "error": {
                    "code": "SUBSCRIPTION_PLAN_NOT_FOUND",
                    "details": None,
                },
            },
            "schema": ErrorResponse.model_json_schema(),
        }
    },
}

_subscription_409 = {
    "description": "Subscription plan name already exists.",
    "content": {
        "application/json": {
            "example": {
                "success": False,
                "message": "Subscription plan already exists",
                "description": "Subscription plan already exists",
                "error": {
                    "code": "SUBSCRIPTION_PLAN_ALREADY_EXISTS",
                    "details": None,
                },
            },
            "schema": ErrorResponse.model_json_schema(),
        }
    },
}

_subscription_422 = {
    "description": "Invalid subscription plan field values.",
    "content": {
        "application/json": {
            "example": {
                "success": False,
                "message": "Request validation failed",
                "description": "Request validation failed",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "details": [
                        {
                            "field": "billing_cycle",
                            "message": "billing_cycle must be monthly or yearly",
                            "msg": "billing_cycle must be monthly or yearly",
                            "type": "value_error",
                            "loc": ["body", "billing_cycle"],
                        }
                    ],
                },
            },
            "schema": ErrorResponse.model_json_schema(),
        }
    },
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
        "Super Admin only. Returns subscription plans for the Manage Subscriptions "
        "table. Each item includes `id`, `name`, `description`, `price`, "
        "`billing_cycle`, `duration`, `status`, and `is_published`. Set "
        "`published_only=true` to return only published plans. Requires Bearer JWT "
        "for Super Admin."
    ),
    tags=["super-admin"],
    responses={
        200: {
            "description": "Subscription plans retrieved.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Subscription plans retrieved",
                        "description": "Subscription plans retrieved successfully.",
                        "email": None,
                        "token": None,
                        "error": None,
                        "data": {
                            "items": [_plan_example],
                            "total": 1,
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
        description="When true, return only published plans.",
        examples=[False],
    ),
    _admin: User = Depends(get_current_super_admin),
    service: SubscriptionPlanService = Depends(get_subscription_plan_service),
) -> dict:
    """Return subscription plans for the Super Admin subscriptions table."""
    items, total = await service.list_plans(published_only=published_only)
    return {
        "success": True,
        "message": "Subscription plans retrieved",
        "description": "Subscription plans retrieved successfully.",
        "email": None,
        "token": None,
        "error": None,
        "data": {
            "items": [item.model_dump(mode="json") for item in items],
            "total": total,
        },
    }


@router.post(
    "",
    response_model=SubscriptionPlanActionResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_subscription_plan",
    summary="Create a subscription plan",
    description=(
        "Super Admin only. Creates a subscription plan with `name`, `price`, and "
        "`billing_cycle`. Optional `description` and `is_published` may be supplied. "
        "Duplicate names return 409 SUBSCRIPTION_PLAN_ALREADY_EXISTS. Invalid field "
        "values return 422 VALIDATION_ERROR. Requires Bearer JWT for Super Admin."
    ),
    tags=["super-admin"],
    responses={
        201: {
            "description": "Subscription plan created.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Subscription plan created",
                        "description": "The subscription plan was added successfully.",
                        "email": None,
                        "token": None,
                        "error": None,
                        "data": {"subscription_plan": _plan_example},
                    }
                }
            },
        },
        **_common_responses,
        409: _subscription_409,
        422: _subscription_422,
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
        "email": None,
        "token": None,
        "error": None,
        "data": {"subscription_plan": plan.model_dump(mode="json")},
    }


@router.put(
    "/{plan_id}",
    response_model=SubscriptionPlanActionResponse,
    status_code=status.HTTP_200_OK,
    operation_id="update_subscription_plan",
    summary="Update a subscription plan",
    description=(
        "Super Admin only. Partially updates a subscription plan identified by "
        "`{plan_id}`. Duplicate names return 409 SUBSCRIPTION_PLAN_ALREADY_EXISTS. "
        "Unknown ids return 404 SUBSCRIPTION_PLAN_NOT_FOUND. Requires Bearer JWT "
        "for Super Admin."
    ),
    tags=["super-admin"],
    responses={
        200: {
            "description": "Subscription plan updated.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Subscription plan updated",
                        "description": "The subscription plan was updated successfully.",
                        "email": None,
                        "token": None,
                        "error": None,
                        "data": {"subscription_plan": _plan_example},
                    }
                }
            },
        },
        **_common_responses,
        404: _subscription_404,
        409: _subscription_409,
        422: _subscription_422,
    },
)
async def update_subscription_plan(
    plan_id: Annotated[
        UUID,
        Path(
            description="UUID of the subscription plan to update.",
            examples=["550e8400-e29b-41d4-a716-446655440000"],
        ),
    ],
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
        "email": None,
        "token": None,
        "error": None,
        "data": {"subscription_plan": plan.model_dump(mode="json")},
    }


@router.delete(
    "/{plan_id}",
    response_model=SubscriptionPlanActionResponse,
    status_code=status.HTTP_200_OK,
    operation_id="delete_subscription_plan",
    summary="Remove a subscription plan",
    description=(
        "Super Admin only. Soft-removes a subscription plan by setting "
        "`is_published` to false and `status` to unpublished. Unknown ids return "
        "404 SUBSCRIPTION_PLAN_NOT_FOUND. Requires Bearer JWT for Super Admin."
    ),
    tags=["super-admin"],
    responses={
        200: {
            "description": "Subscription plan removed.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Subscription plan removed",
                        "description": "The subscription plan was removed successfully.",
                        "email": None,
                        "token": None,
                        "error": None,
                        "data": {
                            "subscription_plan": {
                                **_plan_example,
                                "is_published": False,
                                "status": "unpublished",
                            },
                        },
                    }
                }
            },
        },
        **_common_responses,
        404: _subscription_404,
    },
)
async def delete_subscription_plan(
    plan_id: Annotated[
        UUID,
        Path(
            description="UUID of the subscription plan to remove (soft-unpublish).",
            examples=["550e8400-e29b-41d4-a716-446655440000"],
        ),
    ],
    _admin: User = Depends(get_current_super_admin),
    service: SubscriptionPlanService = Depends(get_subscription_plan_service),
) -> dict:
    """Remove a subscription plan from the published catalog."""
    plan = await service.remove_plan(plan_id)
    return {
        "success": True,
        "message": "Subscription plan removed",
        "description": "The subscription plan was removed successfully.",
        "email": None,
        "token": None,
        "error": None,
        "data": {"subscription_plan": plan.model_dump(mode="json")},
    }
