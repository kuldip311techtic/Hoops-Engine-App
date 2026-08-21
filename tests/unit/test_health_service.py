"""Health service unit tests."""

from unittest.mock import AsyncMock

import pytest

from app.exceptions import AppError
from app.services.health_service import HealthService


def test_liveness_returns_ok() -> None:
    """Liveness does not require a repository."""
    response = HealthService().liveness()
    assert response.success is True
    assert response.data.status == "ok"


@pytest.mark.asyncio
async def test_readiness_success() -> None:
    """Readiness succeeds when the repository ping returns True."""
    repo = AsyncMock()
    repo.ping = AsyncMock(return_value=True)
    service = HealthService(repository=repo)
    response = await service.readiness()
    assert response.success is True
    assert response.message == "Service is ready"


@pytest.mark.asyncio
async def test_readiness_unavailable_on_false() -> None:
    """Readiness raises DATABASE_UNAVAILABLE when ping is false."""
    repo = AsyncMock()
    repo.ping = AsyncMock(return_value=False)
    service = HealthService(repository=repo)
    with pytest.raises(AppError) as exc_info:
        await service.readiness()
    assert exc_info.value.code == "DATABASE_UNAVAILABLE"
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_readiness_unavailable_on_error() -> None:
    """Readiness does not leak database exceptions."""
    repo = AsyncMock()
    repo.ping = AsyncMock(side_effect=RuntimeError("connection refused"))
    service = HealthService(repository=repo)
    with pytest.raises(AppError) as exc_info:
        await service.readiness()
    assert exc_info.value.code == "DATABASE_UNAVAILABLE"
    assert "connection refused" not in exc_info.value.message
