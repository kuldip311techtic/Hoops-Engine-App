"""In-memory repositories for fast unit and HTTP tests."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.models.organization import Organization
from app.models.support_request import SupportRequest, SupportRequestStatus
from app.models.user import User, UserRole


class InMemoryUserRepository:
    """Dict-backed user store for tests."""

    def __init__(self) -> None:
        """Initialize an empty store."""
        self._by_email: dict[str, User] = {}
        self._by_id: dict[UUID, User] = {}

    def add(self, user: User) -> User:
        """Persist a user in memory."""
        self._by_email[user.email.lower()] = user
        self._by_id[user.id] = user
        return user

    async def get_by_email(self, email: str) -> User | None:
        """Return the user with this email, or None."""
        return self._by_email.get(email.lower())

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Return the user with this id, or None."""
        return self._by_id.get(user_id)

    async def list_all(
        self,
        *,
        active_only: bool = False,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[User], int]:
        """Return users ordered by email with optional active filter and pagination."""
        rows = list(self._by_id.values())
        if active_only:
            rows = [row for row in rows if row.is_active]
        rows.sort(key=lambda row: row.email)
        total = len(rows)
        return rows[offset : offset + limit], total

    async def create(
        self,
        *,
        email: str,
        password_hash: str,
        role: UserRole = UserRole.USER,
        first_name: str = "",
        last_name: str = "",
    ) -> User:
        """Insert a user in memory."""
        now = datetime.now(UTC)
        user = User(
            id=uuid4(),
            email=email.lower(),
            first_name=first_name,
            last_name=last_name,
            password_hash=password_hash,
            role=role,
            token_version=1,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        return self.add(user)

    async def update(
        self,
        user: User,
        *,
        email: str | None = None,
        password_hash: str | None = None,
        role: UserRole | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> User:
        """Apply partial updates in memory."""
        if email is not None:
            del self._by_email[user.email.lower()]
            user.email = email.lower()
            self._by_email[user.email] = user
        if password_hash is not None:
            user.password_hash = password_hash
        if role is not None:
            user.role = role
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        user.updated_at = datetime.now(UTC)
        return user

    async def deactivate(self, user: User) -> User:
        """Soft-remove a user in memory."""
        user.is_active = False
        user.updated_at = datetime.now(UTC)
        return user

    async def increment_token_version(self, user: User) -> int:
        """Bump token_version in memory."""
        user.token_version += 1
        return user.token_version


class InMemorySupportRequestRepository:
    """Dict-backed support request store for tests."""

    def __init__(self) -> None:
        """Initialize an empty store."""
        self._by_id: dict[UUID, SupportRequest] = {}

    def add(self, request: SupportRequest) -> SupportRequest:
        """Persist a support request in memory."""
        self._by_id[request.id] = request
        return request

    async def list_all(
        self,
        *,
        status: SupportRequestStatus | None = None,
    ) -> list[SupportRequest]:
        """Return support requests ordered by created_at descending."""
        rows = list(self._by_id.values())
        if status is not None:
            rows = [row for row in rows if row.status == status]
        rows.sort(key=lambda row: row.created_at, reverse=True)
        return rows

    async def count_all(self, *, status: SupportRequestStatus | None = None) -> int:
        """Return the number of support requests."""
        rows = await self.list_all(status=status)
        return len(rows)

    async def get_by_id(self, request_id: UUID) -> SupportRequest | None:
        """Return the support request with this id, or None."""
        return self._by_id.get(request_id)

    async def create(
        self,
        *,
        subject: str,
        message: str,
        submitter_user_id: UUID | None = None,
        status: SupportRequestStatus = SupportRequestStatus.OPEN,
    ) -> SupportRequest:
        """Insert a support request row in memory."""
        now = datetime.now(UTC)
        row = SupportRequest(
            id=uuid4(),
            subject=subject,
            message=message,
            submitter_user_id=submitter_user_id,
            status=status,
            created_at=now,
            updated_at=now,
        )
        return self.add(row)

    async def respond(
        self,
        request: SupportRequest,
        admin_response: str,
    ) -> SupportRequest:
        """Record an admin response in memory."""
        now = datetime.now(UTC)
        request.admin_response = admin_response
        request.status = SupportRequestStatus.RESPONDED
        request.responded_at = now
        request.updated_at = now
        return request

    async def close(self, request: SupportRequest) -> SupportRequest:
        """Mark the support request closed in memory."""
        now = datetime.now(UTC)
        request.status = SupportRequestStatus.CLOSED
        request.closed_at = now
        request.updated_at = now
        return request


class InMemoryOrganizationRepository:
    """Dict-backed organization store for tests."""

    def __init__(self) -> None:
        """Initialize an empty store."""
        self._by_id: dict[UUID, Organization] = {}
        self._by_name: dict[str, Organization] = {}

    def add(self, organization: Organization) -> Organization:
        """Persist an organization in memory."""
        self._by_id[organization.id] = organization
        self._by_name[organization.name] = organization
        return organization

    async def list_all(
        self,
        *,
        active_only: bool = False,
    ) -> list[Organization]:
        """Return organizations ordered by name with optional active filter."""
        rows = list(self._by_id.values())
        if active_only:
            rows = [row for row in rows if row.is_active]
        rows.sort(key=lambda row: row.name)
        return rows

    async def get_by_id(self, organization_id: UUID) -> Organization | None:
        """Return the organization with this id, or None."""
        return self._by_id.get(organization_id)

    async def get_by_name(self, name: str) -> Organization | None:
        """Return the organization with this name, or None."""
        return self._by_name.get(name)

    async def create(
        self,
        *,
        name: str,
        contact_email: str,
        phone_number: str,
        address: str,
    ) -> Organization:
        """Insert an organization in memory."""
        now = datetime.now(UTC)
        organization = Organization(
            id=uuid4(),
            name=name,
            contact_email=contact_email.lower(),
            phone_number=phone_number,
            address=address,
            description=None,
            is_active=True,
            is_published=False,
            created_at=now,
            updated_at=now,
        )
        return self.add(organization)

    async def update(
        self,
        organization: Organization,
        *,
        name: str | None = None,
        contact_email: str | None = None,
        phone_number: str | None = None,
        address: str | None = None,
    ) -> Organization:
        """Apply partial updates in memory."""
        if name is not None:
            del self._by_name[organization.name]
            organization.name = name
            self._by_name[name] = organization
        if contact_email is not None:
            organization.contact_email = contact_email.lower()
        if phone_number is not None:
            organization.phone_number = phone_number
        if address is not None:
            organization.address = address
        organization.updated_at = datetime.now(UTC)
        return organization

    async def deactivate(self, organization: Organization) -> Organization:
        """Soft-remove an organization in memory."""
        organization.is_active = False
        organization.is_published = False
        organization.updated_at = datetime.now(UTC)
        return organization
