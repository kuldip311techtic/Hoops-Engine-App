"""Idempotent Super Admin seed from SUPER_ADMIN_EMAIL / SUPER_ADMIN_PASSWORD."""

import asyncio
import sys

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal, engine
from app.models.user import User, UserRole


async def seed() -> int:
    """Insert the Super Admin when missing. Never prints the password."""
    settings = get_settings()
    if not settings.super_admin_email or not settings.super_admin_password:
        print(
            "SUPER_ADMIN_EMAIL and SUPER_ADMIN_PASSWORD are required",
            file=sys.stderr,
        )
        return 1
    email = settings.super_admin_email.lower()
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()
        if existing is not None:
            print("super admin already exists")
            return 0
        session.add(
            User(
                email=email,
                password_hash=hash_password(settings.super_admin_password),
                role=UserRole.SUPER_ADMIN,
            )
        )
        await session.commit()
    print("super admin seeded")
    return 0


async def main() -> int:
    """Run seed and dispose the engine."""
    try:
        return await seed()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
