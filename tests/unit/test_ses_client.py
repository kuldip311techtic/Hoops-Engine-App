"""Amazon SES client unit tests (boto3 is mocked)."""

from unittest.mock import MagicMock

import pytest

from app.clients.ses_client import SESClient
from app.core.config import Settings
from app.exceptions import EmailDeliveryError, EmailNotConfiguredError


def _settings(**overrides) -> Settings:
    values = {
        "database_url": "postgresql+asyncpg://u:p@localhost/db",
        "test_database_url": "postgresql+asyncpg://u:p@localhost/db_test",
        "secret_key": "s",
        "jwt_secret_key": "k",
        "aws_region": "us-east-1",
        "aws_access_key_id": "AKIATEST",
        "aws_secret_access_key": "secret",
        "ses_from_email": "noreply@example.com",
    }
    values.update(overrides)
    return Settings(**values)


def test_send_email_returns_message_id() -> None:
    """Successful SES send returns the MessageId."""
    client = SESClient(settings=_settings())
    mock_boto = MagicMock()
    mock_boto.send_email.return_value = {"MessageId": "abc-123"}
    client._client = mock_boto
    message_id = client.send_email(
        to_address="user@example.com",
        subject="Hello",
        html_body="<p>Hi</p>",
        text_body="Hi",
    )
    assert message_id == "abc-123"
    mock_boto.send_email.assert_called_once()
    kwargs = mock_boto.send_email.call_args.kwargs
    assert kwargs["Source"] == "noreply@example.com"
    assert kwargs["Destination"]["ToAddresses"] == ["user@example.com"]


def test_send_email_requires_from_address() -> None:
    """Missing SES from-address raises EmailNotConfiguredError."""
    client = SESClient(settings=_settings(ses_from_email=""))
    client._client = MagicMock()
    with pytest.raises(EmailNotConfiguredError) as exc_info:
        client.send_email(
            to_address="user@example.com",
            subject="Hello",
            html_body="<p>Hi</p>",
        )
    assert exc_info.value.code == "EMAIL_NOT_CONFIGURED"


def test_send_email_wraps_provider_errors() -> None:
    """SES API failures become UI-safe EmailDeliveryError."""
    client = SESClient(settings=_settings())
    mock_boto = MagicMock()
    mock_boto.send_email.side_effect = RuntimeError("AccessDenied")
    client._client = mock_boto
    with pytest.raises(EmailDeliveryError) as exc_info:
        client.send_email(
            to_address="user@example.com",
            subject="Hello",
            html_body="<p>Hi</p>",
        )
    assert exc_info.value.code == "EMAIL_DELIVERY_FAILED"
    assert "AccessDenied" not in exc_info.value.message
