"""Unhandled exception handler must not leak internals."""

import pytest
from starlette.requests import Request

from app.exceptions.handlers import unhandled_exception_handler


@pytest.mark.asyncio
async def test_unhandled_error_does_not_leak_internal_message() -> None:
    """500 responses hide exception text and SQL."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/boom",
        "headers": [],
        "query_string": b"",
    }
    request = Request(scope)
    response = await unhandled_exception_handler(
        request,
        RuntimeError("SELECT * FROM secrets"),
    )
    body = response.body.decode()
    assert response.status_code == 500
    assert "SELECT" not in body
    assert "secrets" not in body
    assert "INTERNAL_ERROR" in body
