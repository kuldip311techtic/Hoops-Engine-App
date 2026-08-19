"""Create users table (recovered orphan revision).

Revision ID: 80955f6a9509
Revises:
Create Date: 2026-08-19

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "80955f6a9509"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create users table matching the existing database schema."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_superadmin", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Drop users table."""
    op.drop_table("users")
