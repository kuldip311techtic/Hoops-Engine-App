"""Legacy scaffold stamp (pre-existing database).

Revision ID: 221ac3649c13
Revises: 0002_auth_tables
Create Date: 2026-08-21

The shared Postgres database is already stamped with this revision from a
prior scaffold. Placing it at head lets Alembic resolve alembic_version and
run autogenerate. Upgrade on a fresh database applies 0001 then 0002 first;
this step is a no-op.
"""

from collections.abc import Sequence

revision: str = "221ac3649c13"
down_revision: str | None = "0002_auth_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No-op; schema changes from the original revision are already applied."""


def downgrade() -> None:
    """No-op."""
