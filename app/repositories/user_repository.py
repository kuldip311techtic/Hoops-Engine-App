"""User persistence."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole


class UserRepository:
    """All user table queries live here."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the async session."""
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        """Return the user with this email, or None."""
        result = await self._session.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Return the user with this id, or None."""
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        email: str,
        password_hash: str,
        role: UserRole = UserRole.USER,
    ) -> User:
        """Insert a new user row and flush so the PK is available."""
        user = User(
            email=email.lower(),
            password_hash=password_hash,
            role=role,
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def increment_token_version(self, user: User) -> int:
        """Bump ``token_version`` so previously issued JWTs are rejected."""
        user.token_version += 1
        await self._session.flush()
        return user.token_version
