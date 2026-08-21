"""Organization admin service unit tests (JAW-9457)."""

from uuid import uuid4

import pytest

from app.exceptions.base import ConflictError, NotFoundError
from app.services.organization_service import OrganizationService
from tests.fakes import InMemoryOrganizationRepository


@pytest.fixture
def organizations() -> InMemoryOrganizationRepository:
    """Empty in-memory organization repository."""
    return InMemoryOrganizationRepository()


@pytest.fixture
def service(organizations: InMemoryOrganizationRepository) -> OrganizationService:
    """OrganizationService bound to in-memory repository without email."""
    return OrganizationService(organizations, email_service=None)


@pytest.mark.asyncio
async def test_create_organization_success(service: OrganizationService) -> None:
    """Creating an organization returns FE-friendly aliases."""
    result = await service.create_organization(
        name="Hoops Academy",
        contact_email="contact@example.com",
        phone_number="1234567890",
        address="123 Main St",
        description="Training org",
        is_published=True,
    )
    assert result.name == "Hoops Academy"
    assert result.email == "contact@example.com"
    assert result.phone == "1234567890"
    assert result.phone_number == "1234567890"
    assert result.is_published is True


@pytest.mark.asyncio
async def test_create_organization_duplicate_name_conflict(
    service: OrganizationService,
) -> None:
    """Duplicate organization names raise ORGANIZATION_ALREADY_EXISTS."""
    await service.create_organization(
        name="Hoops Academy",
        contact_email="a@example.com",
        phone_number="1234567890",
        address="123 Main St",
    )
    with pytest.raises(ConflictError) as exc:
        await service.create_organization(
            name="Hoops Academy",
            contact_email="b@example.com",
            phone_number="9876543210",
            address="456 Oak Ave",
        )
    assert exc.value.code == "ORGANIZATION_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_update_organization_not_found(service: OrganizationService) -> None:
    """Updating a missing organization raises ORGANIZATION_NOT_FOUND."""
    with pytest.raises(NotFoundError) as exc:
        await service.update_organization(uuid4(), name="Missing")
    assert exc.value.code == "ORGANIZATION_NOT_FOUND"


@pytest.mark.asyncio
async def test_remove_organization_deactivates(
    service: OrganizationService,
) -> None:
    """Removing an organization soft-deactivates it."""
    created = await service.create_organization(
        name="Legacy Org",
        contact_email="legacy@example.com",
        phone_number="1112223333",
        address="1 Old Rd",
        is_published=True,
    )
    removed = await service.remove_organization(created.id)
    assert removed.is_active is False
    assert removed.is_published is False


@pytest.mark.asyncio
async def test_list_organizations_published_only_filter(
    service: OrganizationService,
    organizations: InMemoryOrganizationRepository,
) -> None:
    """published_only returns only published active organizations."""
    await organizations.create(
        name="Public Org",
        contact_email="public@example.com",
        phone_number="1234567890",
        address="123 Main St",
        is_published=True,
    )
    await organizations.create(
        name="Draft Org",
        contact_email="draft@example.com",
        phone_number="9876543210",
        address="456 Side St",
        is_published=False,
    )
    published = await service.list_organizations(published_only=True)
    assert len(published) == 1
    assert published[0].name == "Public Org"
