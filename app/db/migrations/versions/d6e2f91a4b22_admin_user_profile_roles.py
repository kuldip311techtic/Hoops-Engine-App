"""Add user profile columns and extend user_role enum.

Revision ID: d6e2f91a4b22
Revises: c5a1d2e84f10
Create Date: 2026-08-21

Note: PostgreSQL enum value additions are irreversible in downgrade.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d6e2f91a4b22"
down_revision: str | None = "c5a1d2e84f10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add first_name/last_name and admin-assignable role enum values."""
    op.add_column(
        "users",
        sa.Column(
            "first_name",
            sa.String(length=100),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "last_name",
            sa.String(length=100),
            nullable=False,
            server_default="",
        ),
    )
    op.alter_column("users", "first_name", server_default=None)
    op.alter_column("users", "last_name", server_default=None)

    for value in ("COACH", "PLAYER", "ORG_ADMIN"):
        op.execute(
            sa.text(f"ALTER TYPE user_role ADD VALUE IF NOT EXISTS '{value}'")
        )


def downgrade() -> None:
    """Drop profile columns. Enum values COACH/PLAYER/ORG_ADMIN remain (irreversible)."""
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
