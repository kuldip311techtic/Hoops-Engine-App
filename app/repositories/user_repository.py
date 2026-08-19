"""User data access layer."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    """Repository for User persistence operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an async database session."""
        self._session = session

    async def list_paginated(
        self,
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[User], int]:
        """Return a last-name-sorted page of users and the total count."""
        count_stmt = select(func.count()).select_from(User)
        total = int((await self._session.execute(count_stmt)).scalar_one())
        stmt = (
            select(User)
            .order_by(User.last_name, User.first_name)
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Return a user by primary key, or None if missing."""
        stmt = select(User).where(User.id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email_ci(
        self,
        email: str,
        *,
        exclude_id: uuid.UUID | None = None,
    ) -> User | None:
        """Return a user whose email matches case-insensitively."""
        stmt = select(User).where(func.lower(User.email) == email.strip().lower())
        if exclude_id is not None:
            stmt = stmt.where(User.id != exclude_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        """Persist a new user and refresh generated fields."""
        self._session.add(user)
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            raise
        await self._session.refresh(user)
        return user

    async def save(self, user: User) -> User:
        """Commit in-place updates and refresh the user."""
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            raise
        await self._session.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        """Permanently remove a user row."""
        await self._session.delete(user)
        await self._session.commit()
