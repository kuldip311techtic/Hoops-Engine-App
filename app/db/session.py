"""Async SQLAlchemy engine and session factory."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

_settings = get_settings()

_engine_kwargs: dict = {}
if _settings.is_test:
    # Avoid pooling asyncpg connections across pytest's per-test event loops.
    _engine_kwargs["poolclass"] = NullPool
else:
    _engine_kwargs["pool_pre_ping"] = True

engine: AsyncEngine = create_async_engine(
    _settings.database_url,
    **_engine_kwargs,
)
AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_async_session() -> AsyncIterator[AsyncSession]:
    """Yield an async session. Prefer ``app.dependencies.db.get_db`` in routes."""
    async with AsyncSessionLocal() as session:
        yield session
