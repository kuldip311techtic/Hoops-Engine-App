"""Verify PostgreSQL database connectivity."""

import asyncio
import sys

from sqlalchemy import text

from app.db.session import get_engine


async def main() -> None:
    """Run a simple SELECT 1 query against the configured database."""
    engine = get_engine()
    async with engine.connect() as connection:
        result = await connection.scalar(text("SELECT 1"))
    if result != 1:
        print("Database connectivity check failed.", file=sys.stderr)
        sys.exit(1)
    print("Database connectivity check passed.")


if __name__ == "__main__":
    asyncio.run(main())
