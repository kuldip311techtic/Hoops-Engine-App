"""Super Admin dashboard analytics schemas."""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import AdminSuccessResponse


class DashboardNavigationLink(BaseModel):
    """Navigation entry for a core Super Admin module."""

    link: str = Field(
        ...,
        description="Client route path for the linked module.",
        examples=["/organizations"],
    )
    description: str = Field(
        ...,
        description="UI-safe label describing the linked module.",
        examples=["Manage organizations"],
    )


class DashboardMetricsData(BaseModel):
    """Aggregated dashboard metrics returned to the Admin FE."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_organizations": 100,
                "total_coaches": 50,
                "total_players": 200,
                "total_sessions": 0,
                "active_subscriptions": 75,
                "revenue_overview": 5000,
                "links": [
                    {
                        "link": "/organizations",
                        "description": "Manage organizations",
                    },
                    {
                        "link": "/users?role=COACH",
                        "description": "Manage coaches",
                    },
                    {
                        "link": "/users?role=PLAYER",
                        "description": "Manage players",
                    },
                    {
                        "link": "/subscriptions",
                        "description": "Manage subscription plans",
                    },
                ],
            }
        }
    )

    total_organizations: int = Field(
        ...,
        ge=0,
        description="Count of active organizations on the platform.",
        examples=[100],
    )
    total_coaches: int = Field(
        ...,
        ge=0,
        description="Count of active users with the Coach role.",
        examples=[50],
    )
    total_players: int = Field(
        ...,
        ge=0,
        description="Count of active users with the Player role.",
        examples=[200],
    )
    total_sessions: int = Field(
        ...,
        ge=0,
        description=(
            "Count of recorded practice sessions. Returns 0 until the Coach "
            "session module is implemented."
        ),
        examples=[0],
    )
    active_subscriptions: int = Field(
        ...,
        ge=0,
        description="Count of user billing subscriptions with ACTIVE status.",
        examples=[75],
    )
    revenue_overview: int = Field(
        ...,
        ge=0,
        description=(
            "Sum of published subscription plan catalog prices (USD, whole "
            "dollars). Placeholder until payment integration exists."
        ),
        examples=[5000],
    )
    links: list[DashboardNavigationLink] = Field(
        default_factory=list,
        description="Navigation links to core Super Admin modules.",
    )


class DashboardResponse(AdminSuccessResponse):
    """Dashboard analytics in the standard success envelope."""

    data: DashboardMetricsData
