"""Organization data access layer."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization


class OrganizationRepository:
    """Repository for Organization persistence operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an async database session."""
        self._session = session

    async def list_paginated(
        self,
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[Organization], int]:
        """Return a name-sorted page of organizations and the total count."""
        count_stmt = select(func.count()).select_from(Organization)
        total = int((await self._session.execute(count_stmt)).scalar_one())
        stmt = (
            select(Organization).order_by(Organization.name).offset(offset).limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_by_id(self, organization_id: uuid.UUID) -> Organization | None:
        """Return an organization by primary key, or None if missing."""
        stmt = select(Organization).where(Organization.id == organization_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name_ci(
        self,
        name: str,
        *,
        exclude_id: uuid.UUID | None = None,
    ) -> Organization | None:
        """Return an organization whose name matches case-insensitively."""
        stmt = select(Organization).where(
            func.lower(Organization.name) == name.strip().lower(),
        )
        if exclude_id is not None:
            stmt = stmt.where(Organization.id != exclude_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email_ci(
        self,
        email: str,
        *,
        exclude_id: uuid.UUID | None = None,
    ) -> Organization | None:
        """Return an organization whose contact email matches case-insensitively."""
        stmt = select(Organization).where(
            func.lower(Organization.contact_email) == email.strip().lower(),
        )
        if exclude_id is not None:
            stmt = stmt.where(Organization.id != exclude_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, organization: Organization) -> Organization:
        """Persist a new organization and refresh generated fields."""
        self._session.add(organization)
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            raise
        await self._session.refresh(organization)
        return organization

    async def save(self, organization: Organization) -> Organization:
        """Commit in-place updates and refresh the organization."""
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            raise
        await self._session.refresh(organization)
        return organization

    async def delete(self, organization: Organization) -> None:
        """Permanently remove an organization row."""
        await self._session.delete(organization)
        await self._session.commit()
