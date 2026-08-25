"""In-memory repositories for fast unit and HTTP tests."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.models.organization import Organization
from app.models.subscription_plan import BillingCycle, SubscriptionPlan
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


class InMemorySubscriptionPlanRepository:
    """Dict-backed subscription plan store for tests."""

    def __init__(self) -> None:
        """Initialize empty plan stores."""
        self._by_id: dict[UUID, SubscriptionPlan] = {}
        self._by_name: dict[str, SubscriptionPlan] = {}

    async def list_all(
        self,
        *,
        published_only: bool = False,
    ) -> list[SubscriptionPlan]:
        """Return plans sorted by name with optional published filter."""
        rows = list(self._by_id.values())
        if published_only:
            rows = [row for row in rows if row.is_published]
        rows.sort(key=lambda row: row.name)
        return rows

    async def get_by_id(self, plan_id: UUID) -> SubscriptionPlan | None:
        """Return the plan with this id, or None."""
        return self._by_id.get(plan_id)

    async def get_by_name(self, name: str) -> SubscriptionPlan | None:
        """Return the plan with this name, or None."""
        return self._by_name.get(name)

    async def create(
        self,
        *,
        name: str,
        price,
        billing_cycle: BillingCycle,
        description: str | None = None,
        is_published: bool = False,
    ) -> SubscriptionPlan:
        """Insert a plan in memory."""
        now = datetime.now(UTC)
        plan = SubscriptionPlan(
            id=uuid4(),
            name=name,
            description=description,
            price=Decimal(str(price)),
            billing_cycle=billing_cycle,
            is_published=is_published,
            created_at=now,
            updated_at=now,
        )
        self._by_id[plan.id] = plan
        self._by_name[plan.name] = plan
        return plan

    async def update(
        self,
        plan: SubscriptionPlan,
        *,
        name: str | None = None,
        description: str | None = None,
        price=None,
        billing_cycle: BillingCycle | None = None,
        is_published: bool | None = None,
    ) -> SubscriptionPlan:
        """Apply partial updates in memory."""
        if name is not None and name != plan.name:
            self._by_name.pop(plan.name, None)
            plan.name = name
            self._by_name[name] = plan
        if description is not None:
            plan.description = description
        if price is not None:
            plan.price = Decimal(str(price))
        if billing_cycle is not None:
            plan.billing_cycle = billing_cycle
        if is_published is not None:
            plan.is_published = is_published
        plan.updated_at = datetime.now(UTC)
        return plan

    async def unpublish(self, plan: SubscriptionPlan) -> SubscriptionPlan:
        """Soft-remove a plan in memory."""
        plan.is_published = False
        plan.updated_at = datetime.now(UTC)
        return plan


class InMemoryAnalyticsRepository:
    """Configurable analytics counts for unit tests."""

    def __init__(
        self,
        *,
        total_organizations: int = 0,
        total_coaches: int = 0,
        total_players: int = 0,
        active_subscriptions: int = 0,
        revenue_overview: Decimal = Decimal(0),
    ) -> None:
        """Initialize dashboard metric counters."""
        self.total_organizations = total_organizations
        self.total_coaches = total_coaches
        self.total_players = total_players
        self.active_subscriptions = active_subscriptions
        self.revenue_overview = revenue_overview

    async def count_active_organizations(self) -> int:
        """Return configured organization count."""
        return self.total_organizations

    async def count_users_by_role(self, role: UserRole) -> int:
        """Return configured role count."""
        if role == UserRole.COACH:
            return self.total_coaches
        if role == UserRole.PLAYER:
            return self.total_players
        return 0

    async def count_active_subscriptions(self) -> int:
        """Return configured active subscription count."""
        return self.active_subscriptions

    async def sum_published_plan_prices(self) -> Decimal:
        """Return configured revenue sum."""
        return self.revenue_overview
