"""Organization management business logic."""

import uuid
from typing import NoReturn

from sqlalchemy.exc import IntegrityError

from app.core.logging import logger
from app.exceptions.base import ConflictError, NotFoundError
from app.models.organization import Organization
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationDeleteResponse,
    OrganizationListData,
    OrganizationListResponse,
    OrganizationRead,
    OrganizationResponse,
    OrganizationUpdate,
)


def _to_read(organization: Organization) -> OrganizationRead:
    """Map an Organization ORM instance to the public read schema."""
    status = "active" if organization.is_active else "inactive"
    email = organization.contact_email
    return OrganizationRead(
        id=organization.id,
        name=organization.name,
        contact_email=email,
        email=email,
        phone_number=organization.phone_number,
        address=organization.address,
        description=organization.description or "",
        status=status,
        is_active=organization.is_active,
    )


def _single_response(
    organization: Organization,
    message: str,
    description: str,
) -> OrganizationResponse:
    """Build the frontend-facing single-organization success envelope."""
    payload = _to_read(organization)
    return OrganizationResponse(
        success=True,
        message=message,
        description=description,
        email=payload.email,
        token=None,
        organization=payload,
        id=payload.id,
        name=payload.name,
        status=payload.status,
        error=None,
        data=payload,
    )


class OrganizationService:
    """Service for Super Admin organization CRUD workflows."""

    def __init__(self, repository: OrganizationRepository) -> None:
        """Initialize with an Organization repository."""
        self._repository = repository

    async def list_organizations(
        self,
        *,
        page: int,
        page_size: int,
    ) -> OrganizationListResponse:
        """Return a paginated list of organizations sorted by name."""
        offset = (page - 1) * page_size
        rows, total = await self._repository.list_paginated(
            offset=offset,
            limit=page_size,
        )
        items = [_to_read(row) for row in rows]
        return OrganizationListResponse(
            success=True,
            message="Organizations retrieved.",
            description="Organization list loaded.",
            email=None,
            token=None,
            organization=None,
            id=None,
            name=None,
            status=None,
            error=None,
            data=OrganizationListData(
                items=items,
                total=total,
                page=page,
                page_size=page_size,
            ),
        )

    async def create_organization(
        self,
        payload: OrganizationCreate,
    ) -> OrganizationResponse:
        """Create an organization, rejecting duplicate name or email."""
        await self._assert_unique(name=payload.name, email=payload.email)
        organization = Organization(
            name=payload.name,
            contact_email=payload.email,
            phone_number=payload.phone_number,
            address=payload.address,
            description=payload.description,
            is_active=payload.is_active,
        )
        try:
            saved = await self._repository.create(organization)
        except IntegrityError as exc:
            logger.warning("Organization create violated a uniqueness constraint")
            await self._raise_duplicate(
                name=payload.name, email=payload.email, cause=exc
            )
        logger.info("Organization created id={} name={}", saved.id, saved.name)
        return _single_response(
            saved,
            message="Organization created.",
            description="Organization added successfully.",
        )

    async def update_organization(
        self,
        organization_id: uuid.UUID,
        payload: OrganizationUpdate,
    ) -> OrganizationResponse:
        """Update an existing organization, rejecting duplicate name or email."""
        organization = await self._get_or_404(organization_id)
        await self._assert_unique(
            name=payload.name,
            email=payload.email,
            exclude_id=organization.id,
        )
        organization.name = payload.name
        organization.contact_email = payload.email
        organization.phone_number = payload.phone_number
        organization.address = payload.address
        organization.description = payload.description
        organization.is_active = payload.is_active
        try:
            saved = await self._repository.save(organization)
        except IntegrityError as exc:
            logger.warning(
                "Organization update violated a uniqueness constraint id={}",
                organization_id,
            )
            await self._raise_duplicate(
                name=payload.name,
                email=payload.email,
                cause=exc,
                exclude_id=organization_id,
            )
        logger.info("Organization updated id={} name={}", saved.id, saved.name)
        return _single_response(
            saved,
            message="Organization updated.",
            description="Organization details saved.",
        )

    async def delete_organization(
        self,
        organization_id: uuid.UUID,
    ) -> OrganizationDeleteResponse:
        """Remove an inactive organization or warn when it is currently in use."""
        organization = await self._get_or_404(organization_id)
        if organization.is_active:
            logger.warning(
                "Attempted to remove active organization id={} name={}",
                organization.id,
                organization.name,
            )
            raise ConflictError(
                message=(
                    "This organization is currently in use and cannot be removed. "
                    "Set status to inactive first."
                ),
                error_code="ORGANIZATION_IN_USE",
                details={"in_use": True, "status": "active"},
            )
        removed_id = organization.id
        removed_name = organization.name
        await self._repository.delete(organization)
        logger.info("Organization removed id={} name={}", removed_id, removed_name)
        return OrganizationDeleteResponse(
            success=True,
            message="Organization removed.",
            description="The organization was removed successfully.",
            email=None,
            token=None,
            organization=None,
            id=removed_id,
            name=removed_name,
            status="inactive",
            error=None,
            data={},
        )

    async def _get_or_404(self, organization_id: uuid.UUID) -> Organization:
        """Load an organization or raise NotFoundError."""
        organization = await self._repository.get_by_id(organization_id)
        if organization is None:
            raise NotFoundError(
                message="Organization not found.",
                error_code="ORGANIZATION_NOT_FOUND",
            )
        return organization

    async def _assert_unique(
        self,
        *,
        name: str,
        email: str,
        exclude_id: uuid.UUID | None = None,
    ) -> None:
        """Raise ConflictError when name or email already belongs to another org."""
        existing_name = await self._repository.get_by_name_ci(
            name,
            exclude_id=exclude_id,
        )
        if existing_name is not None:
            logger.warning("Duplicate organization name={}", name)
            raise ConflictError(
                message="An organization with this name already exists.",
                error_code="ORGANIZATION_NAME_EXISTS",
                details=[
                    {
                        "field": "name",
                        "message": "An organization with this name already exists.",
                    }
                ],
            )
        existing_email = await self._repository.get_by_email_ci(
            email,
            exclude_id=exclude_id,
        )
        if existing_email is not None:
            logger.warning("Duplicate organization email={}", email)
            raise ConflictError(
                message="An organization with this email already exists.",
                error_code="EMAIL_ALREADY_EXISTS",
                details=[
                    {
                        "field": "email",
                        "message": "An organization with this email already exists.",
                    }
                ],
            )

    async def _raise_duplicate(
        self,
        *,
        name: str,
        email: str,
        cause: Exception,
        exclude_id: uuid.UUID | None = None,
    ) -> NoReturn:
        """Map a uniqueness IntegrityError to the matching ConflictError."""
        await self._assert_unique(name=name, email=email, exclude_id=exclude_id)
        raise ConflictError(
            message="An organization with this name or email already exists.",
            error_code="CONFLICT",
        ) from cause
