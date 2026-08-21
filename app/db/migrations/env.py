"""Alembic environment. Sync SQLAlchemy only; URL comes from env / settings."""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, pool

# Discover the directory that contains alembic.ini and the app package.
_here = Path(__file__).resolve()
_package_root = next(
    (
        parent
        for parent in _here.parents
        if (parent / "alembic.ini").is_file() and (parent / "app").is_dir()
    ),
    _here.parents[3],
)
if str(_package_root) not in sys.path:
    sys.path.insert(0, str(_package_root))

from app.core.config import get_settings
from app.db.base import Base
from app.models import Subscription, User  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_sync_url() -> str:
    """Return a sync psycopg2 URL. Never use asyncpg inside Alembic."""
    raw = os.environ.get("DATABASE_URL") or get_settings().database_url
    url = raw.strip().strip('"').strip("'")
    replacements = (
        ("postgresql+asyncpg://", "postgresql+psycopg2://"),
        ("postgres+asyncpg://", "postgresql+psycopg2://"),
        ("postgres://", "postgresql+psycopg2://"),
        ("postgresql://", "postgresql+psycopg2://"),
    )
    for old, new in replacements:
        if url.startswith(old):
            url = new + url[len(old) :]
            break
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=get_sync_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with a sync engine (psycopg2)."""
    connectable = create_engine(get_sync_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
