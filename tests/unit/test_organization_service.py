"""Unit tests for organization management service."""

import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.exceptions.base import ConflictError, NotFoundError
from app.models.organization import Organization
from app.schemas.organization import OrganizationCreate, OrganizationUpdate
from app.services.organization_service import OrganizationService


def _payload(**overrides: object) -> OrganizationCreate:
    """Build a valid organization create payload."""
    data: dict = {
        "name": "Hoops Academy",
        "email": "ops@hoopsacademy.example",
        "phone_number": "+1-555-0100",
        "address": "123 Court Street",
        "description": "Youth basketball training.",
        "status": "active",
    }
    data.update(overrides)
    return OrganizationCreate.model_validate(data)


def _org(**overrides: object) -> Organization:
    """Build an Organization ORM instance."""
    values: dict = {
        "id": uuid.uuid4(),
        "name": "Hoops Academy",
        "contact_email": "ops@hoopsacademy.example",
        "phone_number": "+1-555-0100",
        "address": "123 Court Street",
        "description": "Youth basketball training.",
        "is_active": True,
    }
    values.update(overrides)
    return Organization(**values)


@pytest.fixture
def repository() -> AsyncMock:
    """Provide a mocked OrganizationRepository."""
    return AsyncMock()


@pytest.fixture
def service(repository: AsyncMock) -> OrganizationService:
    """Provide an OrganizationService with a mocked repository."""
    return OrganizationService(repository)


@pytest.mark.asyncio
async def test_create_organization_success(
    service: OrganizationService,
    repository: AsyncMock,
) -> None:
    """Valid details should persist an organization and return envelope fields."""
    created = _org()
    repository.get_by_name_ci.return_value = None
    repository.get_by_email_ci.return_value = None
    repository.create.return_value = created

    response = await service.create_organization(_payload())

    assert response.success is True
    assert response.message == "Organization created."
    assert response.organization is not None
    assert response.email == created.contact_email
    assert response.status == "active"
    assert response.data.name == created.name
    repository.create.assert_awaited()


@pytest.mark.asyncio
async def test_create_organization_duplicate_name_raises_conflict(
    service: OrganizationService,
    repository: AsyncMock,
) -> None:
    """Duplicate names should raise ConflictError with ORGANIZATION_NAME_EXISTS."""
    repository.get_by_name_ci.return_value = _org()
    with pytest.raises(ConflictError) as exc_info:
        await service.create_organization(_payload())
    assert exc_info.value.error_code == "ORGANIZATION_NAME_EXISTS"
    repository.create.assert_not_called()


@pytest.mark.asyncio
async def test_create_organization_duplicate_email_raises_conflict(
    service: OrganizationService,
    repository: AsyncMock,
) -> None:
    """Duplicate emails should raise ConflictError with EMAIL_ALREADY_EXISTS."""
    repository.get_by_name_ci.return_value = None
    repository.get_by_email_ci.return_value = _org()
    with pytest.raises(ConflictError) as exc_info:
        await service.create_organization(_payload())
    assert exc_info.value.error_code == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_create_organization_integrity_error_maps_to_conflict(
    service: OrganizationService,
    repository: AsyncMock,
) -> None:
    """Race-condition unique violations should still return a conflict."""
    repository.get_by_name_ci.return_value = None
    repository.get_by_email_ci.return_value = None
    repository.create.side_effect = IntegrityError("stmt", {}, Exception("dup"))
    with pytest.raises(ConflictError):
        await service.create_organization(_payload())


@pytest.mark.asyncio
async def test_update_organization_not_found(
    service: OrganizationService,
    repository: AsyncMock,
) -> None:
    """Updating a missing organization should raise NotFoundError."""
    repository.get_by_id.return_value = None
    with pytest.raises(NotFoundError) as exc_info:
        await service.update_organization(
            uuid.uuid4(),
            OrganizationUpdate.model_validate(_payload().model_dump()),
        )
    assert exc_info.value.error_code == "ORGANIZATION_NOT_FOUND"


@pytest.mark.asyncio
async def test_delete_organization_in_use_raises_conflict(
    service: OrganizationService,
    repository: AsyncMock,
) -> None:
    """Active organizations are in use and cannot be removed."""
    repository.get_by_id.return_value = _org(is_active=True)
    with pytest.raises(ConflictError) as exc_info:
        await service.delete_organization(uuid.uuid4())
    assert exc_info.value.error_code == "ORGANIZATION_IN_USE"
    assert "currently in use" in exc_info.value.message
    repository.delete.assert_not_called()


@pytest.mark.asyncio
async def test_delete_organization_success(
    service: OrganizationService,
    repository: AsyncMock,
) -> None:
    """Inactive organizations can be removed with a confirmation message."""
    organization = _org(is_active=False)
    repository.get_by_id.return_value = organization
    response = await service.delete_organization(organization.id)
    assert response.success is True
    assert response.message == "Organization removed."
    assert response.id == organization.id
    assert response.name == organization.name
    repository.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_organizations_empty(
    service: OrganizationService,
    repository: AsyncMock,
) -> None:
    """An empty catalog should still return a success envelope."""
    repository.list_paginated.return_value = ([], 0)
    response = await service.list_organizations(page=1, page_size=20)
    assert response.success is True
    assert response.data.items == []
    assert response.data.total == 0
    assert response.error is None
