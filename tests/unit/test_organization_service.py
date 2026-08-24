"""Unit tests for OrganizationService."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.exceptions.base import ConflictError, NotFoundError
from app.models.organization import Organization
from app.services.organization_service import OrganizationService
from tests.fakes import InMemoryOrganizationRepository


@pytest.fixture
def organizations() -> InMemoryOrganizationRepository:
    """Empty in-memory organization repository."""
    return InMemoryOrganizationRepository()


@pytest.fixture
def service(organizations: InMemoryOrganizationRepository) -> OrganizationService:
    """OrganizationService bound to in-memory organizations."""
    return OrganizationService(organizations)


@pytest.fixture
def sample_org(organizations: InMemoryOrganizationRepository) -> Organization:
    """Seed an active organization."""
    now = datetime.now(UTC)
    return organizations.add(
        Organization(
            id=uuid4(),
            name="Organization Name",
            contact_email="contact@example.com",
            phone_number="1234567890",
            address="123 Main St",
            description=None,
            is_active=True,
            is_published=False,
            created_at=now,
            updated_at=now,
        )
    )


@pytest.mark.asyncio
async def test_list_organizations_success(
    service: OrganizationService,
    sample_org: Organization,
) -> None:
    """Listing organizations returns FE-friendly aliases."""
    items, total = await service.list_organizations()
    assert total == 1
    org = items[0]
    assert org.id == sample_org.id
    assert org.name == "Organization Name"
    assert org.organization == "Organization Name"
    assert org.email == "contact@example.com"
    assert org.phone == "1234567890"


@pytest.mark.asyncio
async def test_create_organization_success(service: OrganizationService) -> None:
    """Creating an organization returns the expected response shape."""
    result = await service.create_organization(
        name="New Org",
        contact_email="new@example.com",
        phone_number="9876543210",
        address="456 Oak Ave",
    )
    assert result.name == "New Org"
    assert result.organization == "New Org"
    assert result.email == "new@example.com"
    assert result.phone == "9876543210"
    assert result.address == "456 Oak Ave"


@pytest.mark.asyncio
async def test_create_duplicate_name_raises_conflict(
    service: OrganizationService,
    sample_org: Organization,
) -> None:
    """Duplicate organization names raise ORGANIZATION_ALREADY_EXISTS."""
    with pytest.raises(ConflictError) as exc_info:
        await service.create_organization(
            name=sample_org.name,
            contact_email="other@example.com",
            phone_number="1111111111",
            address="789 Pine St",
        )
    assert exc_info.value.code == "ORGANIZATION_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_update_organization_success(
    service: OrganizationService,
    sample_org: Organization,
) -> None:
    """Updating an organization returns updated fields."""
    result = await service.update_organization(
        sample_org.id,
        name="Updated Org",
        contact_email="updated@example.com",
    )
    assert result.name == "Updated Org"
    assert result.email == "updated@example.com"


@pytest.mark.asyncio
async def test_update_organization_not_found(service: OrganizationService) -> None:
    """Updating unknown organization raises ORGANIZATION_NOT_FOUND."""
    with pytest.raises(NotFoundError) as exc_info:
        await service.update_organization(uuid4(), name="Missing")
    assert exc_info.value.code == "ORGANIZATION_NOT_FOUND"


@pytest.mark.asyncio
async def test_update_inactive_organization_not_found(
    service: OrganizationService,
    organizations: InMemoryOrganizationRepository,
) -> None:
    """Updating inactive organization raises ORGANIZATION_NOT_FOUND."""
    now = datetime.now(UTC)
    org = organizations.add(
        Organization(
            id=uuid4(),
            name="Inactive Org",
            contact_email="inactive@example.com",
            phone_number="2222222222",
            address="111 Closed St",
            description=None,
            is_active=False,
            is_published=False,
            created_at=now,
            updated_at=now,
        )
    )
    with pytest.raises(NotFoundError) as exc_info:
        await service.update_organization(org.id, name="Retry")
    assert exc_info.value.code == "ORGANIZATION_NOT_FOUND"


@pytest.mark.asyncio
async def test_remove_organization_success(
    service: OrganizationService,
    sample_org: Organization,
) -> None:
    """Removing an organization soft-deactivates it."""
    result = await service.remove_organization(sample_org.id)
    assert result.is_active is False


@pytest.mark.asyncio
async def test_remove_organization_not_found(service: OrganizationService) -> None:
    """Removing unknown organization raises ORGANIZATION_NOT_FOUND."""
    with pytest.raises(NotFoundError) as exc_info:
        await service.remove_organization(uuid4())
    assert exc_info.value.code == "ORGANIZATION_NOT_FOUND"
