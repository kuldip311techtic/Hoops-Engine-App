"""Create support_requests table.

Revision ID: 0004_create_support_requests
Revises: 0003_create_organizations
Create Date: 2026-08-19

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_create_support_requests"
down_revision: str | None = "0003_create_organizations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the support_requests table and lookup indexes."""
    op.create_table(
        "support_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_name", sa.String(length=255), nullable=False),
        sa.Column("request", sa.Text(), nullable=False),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'open'"),
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
        "ix_support_requests_user_id",
        "support_requests",
        ["user_id"],
    )
    op.create_index(
        "ix_support_requests_status",
        "support_requests",
        ["status"],
    )
    op.create_index(
        "ix_support_requests_created_at",
        "support_requests",
        ["created_at"],
    )


def downgrade() -> None:
    """Drop the support_requests table."""
    op.drop_index("ix_support_requests_created_at", table_name="support_requests")
    op.drop_index("ix_support_requests_status", table_name="support_requests")
    op.drop_index("ix_support_requests_user_id", table_name="support_requests")
    op.drop_table("support_requests")
