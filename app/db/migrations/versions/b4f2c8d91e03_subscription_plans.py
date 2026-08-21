"""Create subscription_plans catalog table.

Revision ID: b4f2c8d91e03
Revises: a3eb93e2220c
Create Date: 2026-08-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b4f2c8d91e03"
down_revision: str | None = "a3eb93e2220c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

billing_cycle = postgresql.ENUM(
    "MONTHLY",
    "YEARLY",
    name="billing_cycle",
    create_type=False,
)


def upgrade() -> None:
    """Create subscription_plans table for admin-managed offerings."""
    bind = op.get_bind()
    postgresql.ENUM("MONTHLY", "YEARLY", name="billing_cycle").create(
        bind,
        checkfirst=True,
    )
    op.create_table(
        "subscription_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("billing_cycle", billing_cycle, nullable=False),
        sa.Column(
            "is_published",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_subscription_plans_name",
        "subscription_plans",
        ["name"],
        unique=True,
    )


def downgrade() -> None:
    """Drop subscription_plans table."""
    op.drop_index("ix_subscription_plans_name", table_name="subscription_plans")
    op.drop_table("subscription_plans")
    postgresql.ENUM("MONTHLY", "YEARLY", name="billing_cycle").drop(
        op.get_bind(),
        checkfirst=True,
    )
