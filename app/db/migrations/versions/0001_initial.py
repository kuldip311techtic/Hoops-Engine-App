"""Initial migration.

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-21

Baseline revision with no domain tables. Subsequent tickets add models via
follow-up revisions. This migration is reversible (no-op downgrade).
"""

from typing import Sequence, Union

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply the baseline schema (no tables yet)."""
    pass


def downgrade() -> None:
    """Revert the baseline schema."""
    pass
