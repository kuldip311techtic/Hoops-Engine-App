"""Create support_requests table.

Revision ID: a1b2c3d4e5f6
Revises: 5f5c16bc023d
Create Date: 2026-08-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "5f5c16bc023d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

support_request_status = postgresql.ENUM(
    "OPEN",
    "RESPONDED",
    "CLOSED",
    name="support_request_status",
    create_type=False,
)


def upgrade() -> None:
    """Create support_request_status enum and support_requests table."""
    bind = op.get_bind()
    support_request_status.create(bind, checkfirst=True)
    op.create_table(
        "support_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("submitter_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "status",
            support_request_status,
            nullable=False,
            server_default="OPEN",
        ),
        sa.Column("admin_response", sa.Text(), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["submitter_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_support_requests_submitter_user_id",
        "support_requests",
        ["submitter_user_id"],
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
    """Drop support_requests table and enum."""
    op.drop_index("ix_support_requests_created_at", table_name="support_requests")
    op.drop_index("ix_support_requests_status", table_name="support_requests")
    op.drop_index(
        "ix_support_requests_submitter_user_id",
        table_name="support_requests",
    )
    op.drop_table("support_requests")
    support_request_status.drop(op.get_bind(), checkfirst=True)
