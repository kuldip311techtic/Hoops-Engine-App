"""Alembic environment. Uses Settings and a sync URL for migrations."""

from logging.config import fileConfig

from alembic import context
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import engine_from_config, pool, text

from app.core.config import get_settings
from app.db.base import Base
from app import models  # noqa: F401  # register models for autogenerate

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_sync_url() -> str:
    """Rewrite the async DATABASE_URL to a psycopg2 URL for Alembic."""
    settings = get_settings()
    url = settings.database_url
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    return url


def _heal_unknown_database_revision(connection) -> None:
    """Stamp alembic_version to this repo's head when it names a missing revision.

    Autogenerate loads the current DB version from ``alembic_version``. A leftover
    version from a previous scaffold (not present under versions/) raises
    ``Can't locate revision identified by ...``. Aligning to the script head
    lets revision/upgrade proceed without rewriting local history.
    """
    script = ScriptDirectory.from_config(config)
    known = {rev.revision for rev in script.walk_revisions()}
    current = MigrationContext.configure(connection).get_current_heads()
    if not current or all(revision_id in known for revision_id in current):
        return
    head = script.get_current_head()
    if not head:
        return
    connection.execute(
        text("UPDATE alembic_version SET version_num = :version"),
        {"version": head},
    )
    connection.commit()


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
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_sync_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        _heal_unknown_database_revision(connection)
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
