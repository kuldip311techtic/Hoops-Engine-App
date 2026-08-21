"""Billing access-rule unit tests."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User, UserRole
from app.services.auth_service import AuthService


def _user(role: UserRole) -> User:
    """Build an unsaved user."""
    return User(
        id=uuid4(),
        email="u@example.com",
        password_hash="x",
        role=role,
        token_version=1,
        is_active=True,
    )


def test_cancelled_retains_access_until_period_end() -> None:
    """Cancelled subscriptions remain valid before period end."""
    user = _user(UserRole.USER)
    sub = Subscription(
        id=uuid4(),
        user_id=user.id,
        status=SubscriptionStatus.CANCELLED,
        current_period_end=datetime.now(UTC) + timedelta(days=3),
    )
    assert AuthService.subscription_allows_access(user, sub) is True


def test_cancelled_denies_access_after_period_end() -> None:
    """Cancelled subscriptions deny access after period end."""
    user = _user(UserRole.USER)
    sub = Subscription(
        id=uuid4(),
        user_id=user.id,
        status=SubscriptionStatus.CANCELLED,
        current_period_end=datetime.now(UTC) - timedelta(days=1),
    )
    assert AuthService.subscription_allows_access(user, sub) is False


def test_super_admin_not_billed() -> None:
    """Super Admins always have access even with an expired subscription."""
    user = _user(UserRole.SUPER_ADMIN)
    sub = Subscription(
        id=uuid4(),
        user_id=user.id,
        status=SubscriptionStatus.EXPIRED,
        current_period_end=datetime.now(UTC) - timedelta(days=30),
    )
    assert AuthService.subscription_allows_access(user, sub) is True
