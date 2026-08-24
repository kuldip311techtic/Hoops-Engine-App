"""Super Admin dashboard analytics routes."""

from fastapi import APIRouter, Depends, status

from app.dependencies.admin import get_analytics_service, get_current_super_admin
from app.models.user import User
from app.schemas.analytics import DashboardResponse
from app.schemas.common import openapi_error_map
from app.services.analytics_service import AnalyticsService

router = APIRouter()
_errors = openapi_error_map()

_metrics_example = {
    "total_organizations": 100,
    "total_coaches": 50,
    "total_players": 200,
    "total_sessions": 0,
    "active_subscriptions": 75,
    "revenue_overview": 5000,
    "links": [
        {"link": "/organizations", "description": "Manage organizations"},
        {"link": "/users?role=COACH", "description": "Manage coaches"},
        {"link": "/users?role=PLAYER", "description": "Manage players"},
        {"link": "/subscriptions", "description": "Manage subscription plans"},
    ],
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
    response_model=DashboardResponse,
    status_code=status.HTTP_200_OK,
    operation_id="get_dashboard_metrics",
    summary="Get Super Admin dashboard analytics",
    description=(
        "Super Admin only. Returns aggregated platform metrics for the dashboard: "
        "`total_organizations`, `total_coaches`, `total_players`, "
        "`total_sessions`, `active_subscriptions`, and `revenue_overview`. "
        "Includes `links` with client navigation paths to core modules. "
        "`total_sessions` is 0 until the Coach session module is implemented. "
        "`revenue_overview` is the sum of published subscription plan prices. "
        "Returns 404 DASHBOARD_DATA_NOT_AVAILABLE when all countable metrics "
        "are zero. Requires Bearer JWT for Super Admin."
    ),
    tags=["super-admin"],
    responses={
        200: {
            "description": "Dashboard analytics retrieved.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Dashboard analytics retrieved",
                        "description": "Dashboard analytics retrieved successfully.",
                        "email": None,
                        "token": None,
                        "error": None,
                        "data": _metrics_example,
                    }
                }
            },
        },
        404: {
            "description": "No dashboard data is available yet.",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "No dashboard data is available",
                        "description": "No dashboard data is available",
                        "error": {
                            "code": "DASHBOARD_DATA_NOT_AVAILABLE",
                            "details": None,
                        },
                    }
                }
            },
        },
        **_common_responses,
    },
)
async def get_dashboard_metrics(
    _admin: User = Depends(get_current_super_admin),
    service: AnalyticsService = Depends(get_analytics_service),
) -> dict:
    """Return analytics data for the Super Admin dashboard."""
    metrics = await service.get_dashboard_metrics()
    payload = metrics.model_dump(mode="json")
    return {
        "success": True,
        "message": "Dashboard analytics retrieved",
        "description": "Dashboard analytics retrieved successfully.",
        "email": None,
        "token": None,
        "error": None,
        "data": payload,
    }
