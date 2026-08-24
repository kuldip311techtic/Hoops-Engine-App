"""In-memory repositories for fast unit and HTTP tests."""

from uuid import UUID

from app.models.user import User


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

    async def increment_token_version(self, user: User) -> int:
        """Bump token_version in memory."""
        user.token_version += 1
        return user.token_version
