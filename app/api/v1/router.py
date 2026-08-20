"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, organizations, support_requests, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(support_requests.router)
api_router.include_router(users.router)
