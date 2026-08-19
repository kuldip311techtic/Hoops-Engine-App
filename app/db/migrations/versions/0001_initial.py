"""Initial baseline migration.

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-19

"""

from collections.abc import Sequence

revision: str = "0001_initial"
down_revision: str | None = "80955f6a9509"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply baseline migration (no domain tables yet)."""


def downgrade() -> None:
    """Revert baseline migration."""
