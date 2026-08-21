"""Initial migration.

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-21

Empty schema placeholder created during project scaffold. Auth tables land in
0002_auth_tables.
"""

from typing import Sequence, Union

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op initial revision."""
    pass


def downgrade() -> None:
    """No-op downgrade."""
    pass
