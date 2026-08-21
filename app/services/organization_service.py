"""Admin organization use-cases."""

from uuid import UUID

from loguru import logger

from app.exceptions.base import ConflictError, NotFoundError
from app.models.organization import Organization
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.organization import OrganizationResponse
from app.services.email_service import EmailService


class OrganizationService:
    """CRUD operations for organizations. No HTTP here."""

    def __init__(
        self,
        organizations: OrganizationRepository,
        email_service: EmailService | None = None,
    ) -> None:
        """Inject repository and optional email adapter."""
        self._organizations = organizations
        self._email = email_service

    @staticmethod
    def _to_response(organization: Organization) -> OrganizationResponse:
        """Map an ORM row to the admin API response DTO."""
        return OrganizationResponse(
            id=organization.id,
            name=organization.name,
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

    def _notify_created(self, organization: Organization) -> None:
        """Best-effort welcome email to the organization contact. Never fails CRUD."""
        if self._email is None:
            return
        try:
            self._email.send_email(
                to_address=organization.contact_email,
                subject="Welcome to Hoops Engine",
                body_text=(
                    f"Organization '{organization.name}' was registered in Hoops Engine."
                ),
            )
        except Exception:
            logger.warning(
                "organization_welcome_email_skipped org_id={}",
                organization.id,
            )

    async def list_organizations(
        self,
        *,
        active_only: bool = False,
        published_only: bool = False,
    ) -> list[OrganizationResponse]:
        """Return organizations with optional active/published filters."""
        rows = await self._organizations.list_all(
            active_only=active_only,
            published_only=published_only,
        )
        return [self._to_response(row) for row in rows]

    async def get_organization(self, organization_id: UUID) -> OrganizationResponse:
        """Return a single organization or raise NotFoundError."""
        organization = await self._organizations.get_by_id(organization_id)
        if organization is None:
            raise NotFoundError(
                "Organization not found",
                code="ORGANIZATION_NOT_FOUND",
            )
        return self._to_response(organization)

    async def create_organization(
        self,
        *,
        name: str,
        contact_email: str,
        phone_number: str,
        address: str,
        description: str | None = None,
        is_published: bool = False,
    ) -> OrganizationResponse:
        """Create an organization after verifying the name is unique."""
        existing = await self._organizations.get_by_name(name)
        if existing is not None:
            raise ConflictError(
                "An organization with this name already exists",
                code="ORGANIZATION_ALREADY_EXISTS",
            )
        organization = await self._organizations.create(
            name=name,
            contact_email=contact_email,
            phone_number=phone_number,
            address=address,
            description=description,
            is_published=is_published,
        )
        logger.info(
            "organization_created organization_id={} name={}",
            organization.id,
            organization.name,
        )
        self._notify_created(organization)
        return self._to_response(organization)

    async def update_organization(
        self,
        organization_id: UUID,
        *,
        name: str | None = None,
        contact_email: str | None = None,
        phone_number: str | None = None,
        address: str | None = None,
        description: str | None = None,
        is_published: bool | None = None,
    ) -> OrganizationResponse:
        """Update an existing organization."""
        organization = await self._organizations.get_by_id(organization_id)
        if organization is None:
            raise NotFoundError(
                "Organization not found",
                code="ORGANIZATION_NOT_FOUND",
            )
        if not organization.is_active:
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
            name=name,
            contact_email=contact_email,
            phone_number=phone_number,
            address=address,
            description=description,
            is_published=is_published,
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
