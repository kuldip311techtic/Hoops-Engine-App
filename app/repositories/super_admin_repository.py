"""Super Admin data access layer."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.super_admin import SuperAdmin


class SuperAdminRepository:
    """Repository for SuperAdmin persistence operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an async database session."""
        self._session = session

    async def get_by_email(self, email: str) -> SuperAdmin | None:
        """Return a Super Admin by email address (case-insensitive)."""
        normalized_email = email.strip().lower()
        stmt = select(SuperAdmin).where(
            func.lower(SuperAdmin.email) == normalized_email,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
