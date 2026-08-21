"""BillingService access-until-period-end rules."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.exceptions import ForbiddenError
from app.services.billing_service import BillingService


def _service() -> BillingService:
    return BillingService(repository=SimpleNamespace())


def test_cancelled_retains_access_until_period_end() -> None:
    """Cancelled subscription still has access before access_until."""
    future = datetime.now(UTC) + timedelta(days=10)
    sub = SimpleNamespace(status="cancelled", access_until=future)
    snapshot = _service().evaluate(sub)
    assert snapshot.has_access is True
    assert snapshot.status == "cancelled"


def test_cancelled_denies_access_after_period_end() -> None:
    """Cancelled subscription is expired after access_until."""
    past = datetime.now(UTC) - timedelta(days=1)
    sub = SimpleNamespace(status="cancelled", access_until=past)
    snapshot = _service().evaluate(sub)
    assert snapshot.has_access is False
    assert snapshot.status == "expired"
    try:
        _service().ensure_access(snapshot)
        raised = False
    except ForbiddenError as exc:
        raised = True
        assert exc.code == "SUBSCRIPTION_EXPIRED"
    assert raised is True


def test_super_admin_not_billed() -> None:
    """Super Admin login is not gated on a subscription row."""
    snapshot = _service().access_for_super_admin()
    assert snapshot.has_access is True
    assert snapshot.status == "not_applicable"
