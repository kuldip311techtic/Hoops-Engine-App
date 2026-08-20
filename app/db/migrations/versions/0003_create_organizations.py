"""Create organizations table.

Revision ID: 0003_create_organizations
Revises: f6fbce708ad7
Create Date: 2026-08-19

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_create_organizations"
down_revision: str | None = "f6fbce708ad7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the organizations table and uniqueness indexes."""
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("contact_email", sa.String(length=255), nullable=False),
        sa.Column("phone_number", sa.String(length=50), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=False),
        sa.Column(
            "description", sa.Text(), nullable=False, server_default=sa.text("''")
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_organizations_name_lower",
        "organizations",
        [sa.text("lower(name)")],
        unique=True,
    )
    op.create_index(
        "ix_organizations_contact_email_lower",
        "organizations",
        [sa.text("lower(contact_email)")],
        unique=True,
    )


def downgrade() -> None:
    """Drop the organizations table."""
    op.drop_index("ix_organizations_contact_email_lower", table_name="organizations")
    op.drop_index("ix_organizations_name_lower", table_name="organizations")
    op.drop_table("organizations")
