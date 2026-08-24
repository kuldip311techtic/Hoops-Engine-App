"""Admin organization use-cases."""

from uuid import UUID

from loguru import logger

from app.exceptions.base import ConflictError, NotFoundError
from app.models.organization import Organization
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.organization import OrganizationResponse


class OrganizationService:
    """CRUD operations for organizations. No HTTP here."""

    def __init__(self, organizations: OrganizationRepository) -> None:
        """Inject the organization repository."""
        self._organizations = organizations

    @staticmethod
    def _to_response(organization: Organization) -> OrganizationResponse:
        """Map an ORM row to the admin API response DTO."""
        return OrganizationResponse(
            id=organization.id,
            name=organization.name,
            organization=organization.name,
            contact_email=organization.contact_email,
            email=organization.contact_email,
            phone_number=organization.phone_number,
            phone=organization.phone_number,
            address=organization.address,
            description=organization.description,
            is_active=organization.is_active,
            is_published=organization.is_published,
            created_at=organization.created_at,
            updated_at=organization.updated_at,
        )

    async def list_organizations(
        self,
        *,
        active_only: bool = False,
    ) -> tuple[list[OrganizationResponse], int]:
        """Return organizations for the admin table."""
        rows = await self._organizations.list_all(active_only=active_only)
        items = [self._to_response(row) for row in rows]
        return items, len(items)

    async def create_organization(
        self,
        *,
        name: str,
        contact_email: str,
        phone_number: str,
        address: str,
    ) -> OrganizationResponse:
        """Create an organization after verifying the name is unique."""
        existing = await self._organizations.get_by_name(name)
        if existing is not None:
            raise ConflictError(
                "An organization with this name already exists",
                code="ORGANIZATION_ALREADY_EXISTS",
            )
        organization = await self._organizations.create(
            name=name.strip(),
            contact_email=contact_email,
            phone_number=phone_number,
            address=address.strip(),
        )
        logger.info(
            "organization_created organization_id={} name={}",
            organization.id,
            organization.name,
        )
        return self._to_response(organization)

    async def update_organization(
        self,
        organization_id: UUID,
        *,
        name: str | None = None,
        contact_email: str | None = None,
        phone_number: str | None = None,
        address: str | None = None,
    ) -> OrganizationResponse:
        """Update an existing organization."""
        organization = await self._organizations.get_by_id(organization_id)
        if organization is None or not organization.is_active:
            raise NotFoundError(
                "Organization not found",
                code="ORGANIZATION_NOT_FOUND",
            )
        if name is not None and name != organization.name:
            conflict = await self._organizations.get_by_name(name)
            if conflict is not None:
                raise ConflictError(
                    "An organization with this name already exists",
                    code="ORGANIZATION_ALREADY_EXISTS",
                )
        updated = await self._organizations.update(
            organization,
            name=name.strip() if name is not None else None,
            contact_email=contact_email,
            phone_number=phone_number,
            address=address.strip() if address is not None else None,
        )
        logger.info("organization_updated organization_id={}", updated.id)
        return self._to_response(updated)

    async def remove_organization(
        self,
        organization_id: UUID,
    ) -> OrganizationResponse:
        """Soft-remove an organization by deactivating it."""
        organization = await self._organizations.get_by_id(organization_id)
        if organization is None or not organization.is_active:
            raise NotFoundError(
                "Organization not found",
                code="ORGANIZATION_NOT_FOUND",
            )
        updated = await self._organizations.deactivate(organization)
        logger.info("organization_removed organization_id={}", updated.id)
        return self._to_response(updated)
