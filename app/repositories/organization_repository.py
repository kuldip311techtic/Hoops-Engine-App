"""Organization persistence."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization


class OrganizationRepository:
    """All organizations table queries live here."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the async session."""
        self._session = session

    async def list_all(
        self,
        *,
        active_only: bool = False,
        published_only: bool = False,
    ) -> list[Organization]:
        """Return organizations ordered by name with optional filters."""
        stmt = select(Organization).order_by(Organization.name)
        if active_only:
            stmt = stmt.where(Organization.is_active.is_(True))
        if published_only:
            stmt = stmt.where(
                Organization.is_published.is_(True),
                Organization.is_active.is_(True),
            )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, organization_id: UUID) -> Organization | None:
        """Return the organization with this id, or None."""
        result = await self._session.execute(
            select(Organization).where(Organization.id == organization_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Organization | None:
        """Return the organization with this name, or None."""
        result = await self._session.execute(
            select(Organization).where(Organization.name == name)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        name: str,
        contact_email: str,
        phone_number: str,
        address: str,
        description: str | None = None,
        is_published: bool = False,
    ) -> Organization:
        """Insert a new organization row and flush so the PK is available."""
        organization = Organization(
            name=name,
            contact_email=contact_email.lower(),
            phone_number=phone_number,
            address=address,
            description=description,
            is_published=is_published,
        )
        self._session.add(organization)
        await self._session.flush()
        return organization

    async def update(
        self,
        organization: Organization,
        *,
        name: str | None = None,
        contact_email: str | None = None,
        phone_number: str | None = None,
        address: str | None = None,
        description: str | None = None,
        is_published: bool | None = None,
    ) -> Organization:
        """Apply partial updates to an existing organization."""
        if name is not None:
            organization.name = name
        if contact_email is not None:
            organization.contact_email = contact_email.lower()
        if phone_number is not None:
            organization.phone_number = phone_number
        if address is not None:
            organization.address = address
        if description is not None:
            organization.description = description
        if is_published is not None:
            organization.is_published = is_published
        await self._session.flush()
        await self._session.refresh(organization)
        return organization

    async def deactivate(self, organization: Organization) -> Organization:
        """Soft-remove an organization by deactivating and unpublishing it."""
        organization.is_active = False
        organization.is_published = False
        await self._session.flush()
        await self._session.refresh(organization)
        return organization
