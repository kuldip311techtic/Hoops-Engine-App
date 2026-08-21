"""Super Admin data access."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.super_admin import SuperAdmin


class SuperAdminRepository:
    """All Super Admin SQL lives here."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> SuperAdmin | None:
        """Return the Super Admin with this email (case-insensitive), if any."""
        stmt = select(SuperAdmin).where(func.lower(SuperAdmin.email) == email.lower())
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, admin_id: uuid.UUID) -> SuperAdmin | None:
        """Return the Super Admin with this id, if any."""
        stmt = select(SuperAdmin).where(SuperAdmin.id == admin_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, *, email: str, hashed_password: str) -> SuperAdmin:
        """Insert a Super Admin row. Caller must enforce uniqueness first."""
        admin = SuperAdmin(email=email.lower(), hashed_password=hashed_password)
        self._session.add(admin)
        await self._session.flush()
        await self._session.refresh(admin)
        return admin

    async def increment_token_version(self, admin: SuperAdmin) -> SuperAdmin:
        """Bump ``token_version`` so existing JWTs are rejected."""
        admin.token_version = int(admin.token_version) + 1
        await self._session.flush()
        await self._session.refresh(admin)
        return admin

    async def update_password(self, admin: SuperAdmin, hashed_password: str) -> SuperAdmin:
        """Replace the password hash and bump token version."""
        admin.hashed_password = hashed_password
        return await self.increment_token_version(admin)
