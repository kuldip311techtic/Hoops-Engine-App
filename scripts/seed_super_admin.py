"""Seed the initial Super Admin from SUPER_ADMIN_EMAIL / SUPER_ADMIN_PASSWORD.

Usage (from the repo root):

    python -m scripts.seed_super_admin
"""

import asyncio

from app.core.config import get_settings
from app.db.session import dispose_engine, get_session_factory
from app.exceptions import ConflictError
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.super_admin_repository import SuperAdminRepository
from app.services.auth_service import AuthService
from app.services.billing_service import BillingService


async def seed_super_admin() -> None:
    """Create the Super Admin if it does not already exist."""
    settings = get_settings()
    if not settings.super_admin_email or not settings.super_admin_password:
        raise SystemExit("SUPER_ADMIN_EMAIL and SUPER_ADMIN_PASSWORD must be set")
    factory = get_session_factory()
    async with factory() as session:
        service = AuthService(
            repository=SuperAdminRepository(session),
            billing_service=BillingService(SubscriptionRepository(session)),
            settings=settings,
        )
        try:
            admin = await service.register(
                settings.super_admin_email,
                settings.super_admin_password,
            )
            await session.commit()
            print(f"Seeded Super Admin {admin.email}")
        except ConflictError:
            await session.rollback()
            print("Super Admin already exists")
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(seed_super_admin())
