"""Super Admin dependency unit tests."""

from uuid import uuid4

import pytest

from app.dependencies.admin import get_current_super_admin
from app.exceptions.base import ForbiddenError
from app.models.user import User, UserRole


def _user(role: UserRole) -> User:
    """Build a minimal user row."""
    return User(
        id=uuid4(),
        email="test@example.com",
        password_hash="hash",
        role=role,
        token_version=1,
        is_active=True,
    )


@pytest.mark.asyncio
async def test_get_current_super_admin_allows_super_admin() -> None:
    """Super Admin passes the guard."""
    admin = _user(UserRole.SUPER_ADMIN)
    result = await get_current_super_admin(admin)
    assert result is admin


@pytest.mark.asyncio
async def test_get_current_super_admin_rejects_user_role() -> None:
    """Regular users receive 403 FORBIDDEN."""
    with pytest.raises(ForbiddenError) as exc:
        await get_current_super_admin(_user(UserRole.USER))
    assert exc.value.code == "FORBIDDEN"


@pytest.mark.asyncio
async def test_get_current_super_admin_rejects_viewer_role() -> None:
    """Viewers receive 403 FORBIDDEN."""
    with pytest.raises(ForbiddenError) as exc:
        await get_current_super_admin(_user(UserRole.VIEWER))
    assert exc.value.code == "FORBIDDEN"
