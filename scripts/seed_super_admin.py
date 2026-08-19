"""Seed an initial Super Admin account from environment variables."""

import asyncio
import sys

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import get_session_factory
from app.models.super_admin import SuperAdmin


async def main() -> None:
    """Insert a bootstrap Super Admin if configured and not already present."""
    settings = get_settings()
    if not settings.super_admin_email or not settings.super_admin_password:
        print("SUPER_ADMIN_EMAIL and SUPER_ADMIN_PASSWORD not set; skipping seed.")
        return

    session_factory = get_session_factory()
    async with session_factory() as session:
        normalized_email = settings.super_admin_email.strip().lower()
        existing = await session.scalar(
            select(SuperAdmin).where(SuperAdmin.email == normalized_email),
        )
        if existing is not None:
            print(f"Super Admin already exists for email={normalized_email}; skipping.")
            return

        admin = SuperAdmin(
            email=normalized_email,
            hashed_password=hash_password(settings.super_admin_password),
            is_active=True,
        )
        session.add(admin)
        await session.commit()
        print(f"Super Admin seeded for email={normalized_email}.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"Super Admin seed failed: {exc}", file=sys.stderr)
        sys.exit(1)
