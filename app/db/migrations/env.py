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


def _heal_unknown_database_revision(connectable) -> None:
    """Stamp alembic_version onto a known revision when it names a missing one.

    Leftover versions from a previous scaffold raise
    ``Can't locate revision identified by ...``. Stamp to the parent of the
    current head (or head if it has no parent) so ``upgrade head`` can still
    apply pending revisions. Uses a dedicated connection so the SELECT/UPDATE
    cannot leave the migration connection inside an uncommitted transaction
    that would roll back the upgrade.
    """
    script = ScriptDirectory.from_config(config)
    known = {rev.revision for rev in script.walk_revisions()}
    with connectable.connect() as connection:
        current = MigrationContext.configure(connection).get_current_heads()
        if not current or all(revision_id in known for revision_id in current):
            connection.rollback()
            return
        head = script.get_current_head()
        if not head:
            connection.rollback()
            return
        head_script = script.get_revision(head)
        stamp_to = head
        if head_script is not None and head_script.down_revision:
            down = head_script.down_revision
            if isinstance(down, tuple):
                down = down[0]
            if down in known:
                stamp_to = down
        connection.execute(
            text("UPDATE alembic_version SET version_num = :version"),
            {"version": stamp_to},
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

    _heal_unknown_database_revision(connectable)

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
