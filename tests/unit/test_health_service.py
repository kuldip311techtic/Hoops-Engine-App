"""HealthService unit tests."""

from unittest.mock import AsyncMock

import pytest

from app.exceptions.base import ServiceUnavailableError
from app.services.health_service import HealthService


@pytest.mark.asyncio
async def test_liveness_returns_ok() -> None:
    """Liveness does not need a repository."""
    assert await HealthService().liveness() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readiness_success() -> None:
    """Readiness succeeds when ping returns True."""
    repo = AsyncMock()
    repo.ping = AsyncMock(return_value=True)
    result = await HealthService(repo).readiness()
    assert result == {"status": "ok"}


@pytest.mark.asyncio
async def test_readiness_unavailable_on_false() -> None:
    """Readiness raises when ping returns False."""
    repo = AsyncMock()
    repo.ping = AsyncMock(return_value=False)
    with pytest.raises(ServiceUnavailableError):
        await HealthService(repo).readiness()
