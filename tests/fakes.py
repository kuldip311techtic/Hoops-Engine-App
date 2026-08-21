"""In-memory repositories for tests."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.models.organization import Organization
from app.models.subscription import Subscription
from app.models.subscription_plan import BillingCycle, SubscriptionPlan
from app.models.user import User, UserRole


class InMemoryUserRepository:
    """Dict-backed UserRepository stand-in."""

    def __init__(self) -> None:
        """Create an empty user map."""
        self.users: dict[str, User] = {}
        self.by_id: dict[UUID, User] = {}

    async def get_by_email(self, email: str) -> User | None:
        """Lookup by lowercase email."""
        return self.users.get(email.lower())

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Lookup by id."""
        return self.by_id.get(user_id)

    async def create(
        self,
        *,
        email: str,
        password_hash: str,
        role: UserRole = UserRole.USER,
        first_name: str = "",
        last_name: str = "",
    ) -> User:
        """Insert a user."""
        user = User(
            id=uuid4(),
            email=email.lower(),
            first_name=first_name,
            last_name=last_name,
            password_hash=password_hash,
            role=role,
            token_version=1,
            is_active=True,
        )
        self.users[user.email] = user
        self.by_id[user.id] = user
        return user

    async def list_all(
        self,
        *,
        active_only: bool = False,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[User], int]:
        """Return users with optional active filter and pagination."""
        rows = list(self.by_id.values())
        if active_only:
            rows = [row for row in rows if row.is_active]
        rows.sort(key=lambda row: row.email)
        total = len(rows)
        return rows[offset : offset + limit], total

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
        """Apply partial updates."""
        if email is not None and email.lower() != user.email:
            self.users.pop(user.email, None)
            user.email = email.lower()
            self.users[user.email] = user
        if password_hash is not None:
            user.password_hash = password_hash
        if role is not None:
            user.role = role
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        return user

    async def deactivate(self, user: User) -> User:
        """Soft-remove a user."""
        user.is_active = False
        return user

    async def increment_token_version(self, user: User) -> int:
        """Bump token_version."""
        user.token_version += 1
        return user.token_version

    def add(self, user: User) -> User:
        """Register an already-built user."""
        if user.id is None:
            user.id = uuid4()
        self.users[user.email.lower()] = user
        self.by_id[user.id] = user
        return user


class InMemorySubscriptionRepository:
    """Dict-backed SubscriptionRepository stand-in."""

    def __init__(self) -> None:
        """Create an empty subscription map."""
        self.items: dict[UUID, Subscription] = {}

    async def get_by_user_id(self, user_id: UUID) -> Subscription | None:
        """Lookup by user id."""
        return self.items.get(user_id)

    async def upsert(self, **kwargs) -> Subscription:
        """Create or replace a subscription."""
        user_id = kwargs["user_id"]
        existing = self.items.get(user_id)
        if existing is None:
            existing = Subscription(id=uuid4(), **kwargs)
        else:
            existing.status = kwargs["status"]
            existing.current_period_end = kwargs["current_period_end"]
            existing.cancelled_at = kwargs.get("cancelled_at")
        self.items[user_id] = existing
        return existing


class InMemorySubscriptionPlanRepository:
    """Dict-backed SubscriptionPlanRepository stand-in."""

    def __init__(self) -> None:
        """Create empty plan stores."""
        self.by_id: dict[UUID, SubscriptionPlan] = {}
        self.by_name: dict[str, SubscriptionPlan] = {}

    async def list_all(self, *, published_only: bool = False) -> list[SubscriptionPlan]:
        """Return plans sorted by name."""
        rows = list(self.by_id.values())
        if published_only:
            rows = [row for row in rows if row.is_published]
        return sorted(rows, key=lambda row: row.name)

    async def get_by_id(self, plan_id: UUID) -> SubscriptionPlan | None:
        """Lookup by id."""
        return self.by_id.get(plan_id)

    async def get_by_name(self, name: str) -> SubscriptionPlan | None:
        """Lookup by name."""
        return self.by_name.get(name)

    async def create(
        self,
        *,
        name: str,
        price,
        billing_cycle: BillingCycle,
        description: str | None = None,
        is_published: bool = False,
    ) -> SubscriptionPlan:
        """Insert a plan."""
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
        self.by_id[plan.id] = plan
        self.by_name[plan.name] = plan
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
        """Apply partial updates."""
        if name is not None and name != plan.name:
            self.by_name.pop(plan.name, None)
            plan.name = name
            self.by_name[name] = plan
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
        """Mark plan unpublished."""
        plan.is_published = False
        plan.updated_at = datetime.now(UTC)
        return plan


class InMemoryOrganizationRepository:
    """Dict-backed OrganizationRepository stand-in."""

    def __init__(self) -> None:
        """Create empty organization stores."""
        self.by_id: dict[UUID, Organization] = {}
        self.by_name: dict[str, Organization] = {}

    async def list_all(
        self,
        *,
        active_only: bool = False,
        published_only: bool = False,
    ) -> list[Organization]:
        """Return organizations sorted by name."""
        rows = list(self.by_id.values())
        if active_only:
            rows = [row for row in rows if row.is_active]
        if published_only:
            rows = [
                row for row in rows if row.is_published and row.is_active
            ]
        return sorted(rows, key=lambda row: row.name)

    async def get_by_id(self, organization_id: UUID) -> Organization | None:
        """Lookup by id."""
        return self.by_id.get(organization_id)

    async def get_by_name(self, name: str) -> Organization | None:
        """Lookup by name."""
        return self.by_name.get(name)

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
        """Insert an organization."""
        now = datetime.now(UTC)
        organization = Organization(
            id=uuid4(),
            name=name,
            contact_email=contact_email.lower(),
            phone_number=phone_number,
            address=address,
            description=description,
            is_published=is_published,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self.by_id[organization.id] = organization
        self.by_name[organization.name] = organization
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
        """Apply partial updates."""
        if name is not None and name != organization.name:
            self.by_name.pop(organization.name, None)
            organization.name = name
            self.by_name[name] = organization
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
        organization.updated_at = datetime.now(UTC)
        return organization

    async def deactivate(self, organization: Organization) -> Organization:
        """Soft-remove an organization."""
        organization.is_active = False
        organization.is_published = False
        organization.updated_at = datetime.now(UTC)
        return organization
