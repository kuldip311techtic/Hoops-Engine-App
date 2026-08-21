"""Database session FastAPI dependencies."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db as _get_db


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped async database session."""
    async for session in _get_db():
        yield session
