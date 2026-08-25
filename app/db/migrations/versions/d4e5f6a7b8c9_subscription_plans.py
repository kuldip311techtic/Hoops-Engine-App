"""Recreate subscription_plans catalog table.

Revision ID: d4e5f6a7b8c9
Revises: 80a9ba7ca08b
Create Date: 2026-08-24 13:40:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "80a9ba7ca08b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_billing_cycle_enum = postgresql.ENUM(
    "MONTHLY",
    "YEARLY",
    name="billing_cycle",
    create_type=False,
)


def upgrade() -> None:
    """Create billing_cycle enum and subscription_plans table if missing."""
    bind = op.get_bind()
    billing_cycle = postgresql.ENUM(
        "MONTHLY",
        "YEARLY",
        name="billing_cycle",
        create_type=False,
    )
    billing_cycle.create(bind, checkfirst=True)
    op.create_table(
        "subscription_plans",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("billing_cycle", _billing_cycle_enum, nullable=False),
        sa.Column(
            "is_published",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )


def downgrade() -> None:
    """Drop subscription_plans table."""
    op.drop_table("subscription_plans")
