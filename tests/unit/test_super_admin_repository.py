"""Unit tests for SuperAdminRepository."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.super_admin import SuperAdmin
from app.repositories.super_admin_repository import SuperAdminRepository


@pytest.mark.asyncio
async def test_get_by_id_returns_admin() -> None:
    """get_by_id should return the Super Admin loaded from the session."""
    admin_id = uuid.uuid4()
    admin = SuperAdmin(
        id=admin_id,
        email="admin@example.com",
        hashed_password="hash",
        is_active=True,
    )
    result = MagicMock()
    result.scalar_one_or_none.return_value = admin
    session = AsyncMock()
    session.execute.return_value = result

    repository = SuperAdminRepository(session)
    found = await repository.get_by_id(admin_id)

    assert found is admin
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_missing() -> None:
    """get_by_id should return None when no row matches."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session = AsyncMock()
    session.execute.return_value = result

    repository = SuperAdminRepository(session)
    found = await repository.get_by_id(uuid.uuid4())

    assert found is None
