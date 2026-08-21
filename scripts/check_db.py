"""Verify PostgreSQL connectivity with a ``SELECT 1`` probe.

Usage (from the repo root, with DATABASE_URL set):

    python -m scripts.check_db
"""

import asyncio

from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import dispose_engine, get_session_factory


async def check_database() -> None:
    """Run a test query and print a UI-safe result (no credentials)."""
    settings = get_settings()
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(text("SELECT 1"))
        value = result.scalar_one()
    await dispose_engine()
    if value != 1:
        raise SystemExit("Database probe failed")
    env = settings.environment
    print(f"Database connectivity ok (environment={env})")


if __name__ == "__main__":
    asyncio.run(check_database())
