"""Reconcile live schema with User and Subscription models.

Revision ID: a3eb93e2220c
Revises: ac03be72f0af
Create Date: 2026-08-21 16:25:43.138725
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a3eb93e2220c"
down_revision: Union[str, None] = "ac03be72f0af"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

user_role = postgresql.ENUM(
    "SUPER_ADMIN",
    "USER",
    "VIEWER",
    name="user_role",
    create_type=False,
)
subscription_status = postgresql.ENUM(
    "ACTIVE",
    "CANCELLED",
    "EXPIRED",
    name="subscription_status",
    create_type=False,
)


def upgrade() -> None:
    """Create enums first, then reshape users/subscriptions to match models."""
    bind = op.get_bind()
    postgresql.ENUM(
        "SUPER_ADMIN", "USER", "VIEWER", name="user_role"
    ).create(bind, checkfirst=True)
    postgresql.ENUM(
        "ACTIVE", "CANCELLED", "EXPIRED", name="subscription_status"
    ).create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column(
            "token_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
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
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.execute(
        sa.text(
            """
            INSERT INTO users (
                id, email, password_hash, role, token_version, is_active,
                created_at, updated_at
            )
            SELECT
                id,
                email,
                hashed_password,
                'SUPER_ADMIN'::user_role,
                COALESCE(token_version, 1),
                TRUE,
                created_at,
                updated_at
            FROM super_admins
            ON CONFLICT (email) DO NOTHING
            """
        )
    )

    op.add_column(
        "subscriptions",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column(
            "current_period_end",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.execute(
        sa.text(
            """
            UPDATE subscriptions AS s
            SET user_id = u.id,
                current_period_end = COALESCE(s.access_until, NOW())
            FROM users AS u
            WHERE lower(u.email) = lower(s.email)
            """
        )
    )
    op.execute(sa.text("DELETE FROM subscriptions WHERE user_id IS NULL"))
    op.alter_column(
        "subscriptions",
        "user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.alter_column(
        "subscriptions",
        "current_period_end",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE subscriptions
            ALTER COLUMN status TYPE subscription_status
            USING upper(status)::subscription_status
            """
        )
    )
    op.drop_index(op.f("ix_subscriptions_email"), table_name="subscriptions")
    op.create_unique_constraint(
        "subscriptions_user_id_key", "subscriptions", ["user_id"]
    )
    op.create_foreign_key(
        "subscriptions_user_id_fkey",
        "subscriptions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_column("subscriptions", "provider_ref")
    op.drop_column("subscriptions", "access_until")
    op.drop_column("subscriptions", "updated_at")
    op.drop_column("subscriptions", "email")
    op.drop_index(op.f("ix_super_admins_email"), table_name="super_admins")
    op.drop_table("super_admins")


def downgrade() -> None:
    """Restore the pre-model super_admins / email-keyed subscriptions shape."""
    op.create_table(
        "super_admins",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.VARCHAR(length=255), nullable=False),
        sa.Column("hashed_password", sa.VARCHAR(length=255), nullable=False),
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
        sa.Column(
            "token_version",
            sa.INTEGER(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="super_admins_pkey"),
    )
    op.create_index(
        op.f("ix_super_admins_email"), "super_admins", ["email"], unique=True
    )
    op.execute(
        sa.text(
            """
            INSERT INTO super_admins (
                id, email, hashed_password, created_at, updated_at, token_version
            )
            SELECT
                id, email, password_hash, created_at, updated_at, token_version
            FROM users
            WHERE role = 'SUPER_ADMIN'::user_role
            """
        )
    )

    op.add_column(
        "subscriptions",
        sa.Column("email", sa.VARCHAR(length=255), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "subscriptions",
        sa.Column(
            "access_until",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "subscriptions",
        sa.Column("provider_ref", sa.VARCHAR(length=255), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE subscriptions AS s
            SET email = u.email,
                access_until = s.current_period_end
            FROM users AS u
            WHERE u.id = s.user_id
            """
        )
    )
    op.execute(sa.text("DELETE FROM subscriptions WHERE email IS NULL"))
    op.alter_column(
        "subscriptions",
        "email",
        existing_type=sa.VARCHAR(length=255),
        nullable=False,
    )
    op.drop_constraint(
        "subscriptions_user_id_fkey", "subscriptions", type_="foreignkey"
    )
    op.drop_constraint(
        "subscriptions_user_id_key", "subscriptions", type_="unique"
    )
    op.create_index(
        op.f("ix_subscriptions_email"), "subscriptions", ["email"], unique=True
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE subscriptions
            ALTER COLUMN status TYPE VARCHAR(32)
            USING status::text
            """
        )
    )
    op.drop_column("subscriptions", "current_period_end")
    op.drop_column("subscriptions", "user_id")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    postgresql.ENUM(name="subscription_status").drop(
        op.get_bind(), checkfirst=True
    )
    postgresql.ENUM(name="user_role").drop(op.get_bind(), checkfirst=True)
