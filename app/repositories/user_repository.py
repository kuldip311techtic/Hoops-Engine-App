"""User persistence."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
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

    async def list_all(
        self,
        *,
        active_only: bool = False,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[User], int]:
        """Return users ordered by email with optional active filter and pagination."""
        filters = []
        if active_only:
            filters.append(User.is_active.is_(True))
        count_stmt = select(func.count()).select_from(User)
        if filters:
            count_stmt = count_stmt.where(*filters)
        total = int((await self._session.execute(count_stmt)).scalar_one())
        stmt = select(User).order_by(User.email).offset(offset).limit(limit)
        if filters:
            stmt = stmt.where(*filters)
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def create(
        self,
        *,
        email: str,
        password_hash: str,
        role: UserRole = UserRole.USER,
        first_name: str = "",
        last_name: str = "",
    ) -> User:
        """Insert a new user row and flush so the PK is available."""
        user = User(
            email=email.lower(),
            first_name=first_name,
            last_name=last_name,
            password_hash=password_hash,
            role=role,
        )
        self._session.add(user)
        await self._session.flush()
        return user

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
        """Apply partial updates to a user row."""
        if email is not None:
            user.email = email.lower()
        if password_hash is not None:
            user.password_hash = password_hash
        if role is not None:
            user.role = role
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        user.updated_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def deactivate(self, user: User) -> User:
        """Soft-remove a user by marking the account inactive."""
        user.is_active = False
        user.updated_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def increment_token_version(self, user: User) -> int:
        """Bump ``token_version`` so previously issued JWTs are rejected."""
        user.token_version += 1
        user.updated_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(user)
        return user.token_version
