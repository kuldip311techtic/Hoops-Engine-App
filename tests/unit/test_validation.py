"""Example request validation schema tests."""

import pytest
from pydantic import ValidationError

from app.schemas.example import ExampleUser


def test_example_user_validates_required_fields() -> None:
    """ExampleUser accepts well-formed input."""
    user = ExampleUser(username="coach_jane", email="coach@example.com")
    assert user.username == "coach_jane"


def test_example_user_missing_username_raises() -> None:
    """Missing username produces a validation error."""
    with pytest.raises(ValidationError) as exc_info:
        ExampleUser(email="coach@example.com")  # type: ignore[call-arg]
    errors = exc_info.value.errors()
    assert any(err["loc"] == ("username",) for err in errors)
