"""Verify PostgreSQL connectivity with a SELECT 1 query."""

import asyncio
import sys

from sqlalchemy import text

from app.db.session import engine


async def main() -> int:
    """Run a test query and print ok on success."""
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - CLI diagnostic
        print(f"database check failed: {exc.__class__.__name__}", file=sys.stderr)
        return 1
    finally:
        await engine.dispose()
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
