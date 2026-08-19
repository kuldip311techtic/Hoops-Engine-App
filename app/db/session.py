"""Async database engine and session management."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
_test_engine: AsyncEngine | None = None
_test_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the primary async database engine."""
    global _engine, _session_factory
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_pre_ping=True,
        )
        _session_factory = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the primary async session factory."""
    get_engine()
    assert _session_factory is not None
    return _session_factory


def get_test_engine() -> AsyncEngine:
    """Return the test async database engine."""
    global _test_engine, _test_session_factory
    if _test_engine is None:
        settings = get_settings()
        test_url = settings.test_database_url or settings.database_url
        _test_engine = create_async_engine(
            test_url,
            echo=False,
            pool_pre_ping=True,
        )
        _test_session_factory = async_sessionmaker(
            bind=_test_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return _test_engine


def get_test_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the test async session factory."""
    get_test_engine()
    assert _test_session_factory is not None
    return _test_session_factory


async def get_async_session() -> AsyncIterator[AsyncSession]:
    """Yield an async database session for request-scoped dependency injection."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
