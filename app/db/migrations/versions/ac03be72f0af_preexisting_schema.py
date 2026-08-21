"""Pre-existing database stamp.

Revision ID: ac03be72f0af
Revises: 0002_auth_tables
Create Date: 2026-08-21

The shared Postgres database is already stamped with this revision. Placing it
at head lets Alembic resolve alembic_version and run autogenerate. Upgrade on a
fresh database still applies 0001 then 0002 first; this step is a no-op.
"""

from collections.abc import Sequence

revision: str = "ac03be72f0af"
down_revision: str | None = "0002_auth_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No-op; this id matches the stamp already stored in alembic_version."""


def downgrade() -> None:
    """No-op; returning to 0002_auth_tables does not alter schema."""
