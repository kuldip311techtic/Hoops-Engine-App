"""EmailService unit tests."""

from unittest.mock import MagicMock

import pytest

from app.core.config import Settings
from app.exceptions import EmailNotConfiguredError
from app.services.email_service import EmailService


def _settings(**overrides) -> Settings:
    values = {
        "database_url": "postgresql+asyncpg://u:p@localhost/db",
        "test_database_url": "postgresql+asyncpg://u:p@localhost/db_test",
        "secret_key": "s",
        "jwt_secret_key": "k",
        "aws_access_key_id": "AKIATEST",
        "aws_secret_access_key": "secret",
        "ses_from_email": "noreply@example.com",
    }
    values.update(overrides)
    return Settings(**values)


def test_send_email_delegates_to_ses_client() -> None:
    """EmailService calls the SES client and returns the message id."""
    ses = MagicMock()
    ses.send_email.return_value = "mid-1"
    service = EmailService(ses_client=ses, settings=_settings())
    result = service.send_email(
        to_address="user@example.com",
        subject="Welcome",
        html_body="<p>Welcome</p>",
    )
    assert result == "mid-1"
    ses.send_email.assert_called_once()


def test_send_email_not_configured() -> None:
    """EmailService refuses to send when SES credentials are missing."""
    ses = MagicMock()
    service = EmailService(
        ses_client=ses,
        settings=_settings(aws_access_key_id="", aws_secret_access_key=""),
    )
    with pytest.raises(EmailNotConfiguredError):
        service.send_email(
            to_address="user@example.com",
            subject="Welcome",
            html_body="<p>Welcome</p>",
        )
    ses.send_email.assert_not_called()
