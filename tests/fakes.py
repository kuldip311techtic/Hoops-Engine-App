"""In-memory repositories for tests."""

from uuid import UUID, uuid4

from app.models.subscription import Subscription
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
    ) -> User:
        """Insert a user."""
        user = User(
            id=uuid4(),
            email=email.lower(),
            password_hash=password_hash,
            role=role,
            token_version=1,
            is_active=True,
        )
        self.users[user.email] = user
        self.by_id[user.id] = user
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
