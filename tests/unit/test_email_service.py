"""EmailService / SESClient unit tests."""

from unittest.mock import MagicMock, patch

import pytest

from app.clients.ses_client import SESClient
from app.core.config import Settings
from app.exceptions.base import AppError, ServiceUnavailableError
from app.services.email_service import EmailService


def test_send_email_not_configured() -> None:
    """Missing SES_FROM_EMAIL raises EMAIL_NOT_CONFIGURED."""
    client = SESClient(Settings(ses_from_email="", jwt_secret_key="x"))
    with pytest.raises(ServiceUnavailableError) as exc:
        client.send_email(to_address="a@b.com", subject="Hi", body_text="x")
    assert exc.value.code == "EMAIL_NOT_CONFIGURED"


def test_send_email_returns_message_id() -> None:
    """Provider MessageId is returned on success."""
    settings = Settings(ses_from_email="from@example.com", jwt_secret_key="x")
    client = SESClient(settings)
    fake = MagicMock()
    fake.send_email.return_value = {"MessageId": "mid-1"}
    with patch.object(SESClient, "_client", return_value=fake):
        assert client.send_email(to_address="a@b.com", subject="Hi", body_text="x") == "mid-1"


def test_send_email_wraps_provider_errors() -> None:
    """boto3 failures become EMAIL_SEND_FAILED without leaking internals."""
    settings = Settings(ses_from_email="from@example.com", jwt_secret_key="x")
    client = SESClient(settings)
    fake = MagicMock()
    fake.send_email.side_effect = RuntimeError("aws exploded")
    with patch.object(SESClient, "_client", return_value=fake):
        with pytest.raises(AppError) as exc:
            client.send_email(to_address="a@b.com", subject="Hi", body_text="x")
    assert exc.value.code == "EMAIL_SEND_FAILED"
    assert "aws exploded" not in exc.value.message


def test_send_email_delegates_to_ses_client() -> None:
    """EmailService delegates to the SES adapter."""
    ses = MagicMock()
    ses.send_email.return_value = "mid-2"
    service = EmailService(client=ses)
    assert service.send_email(to_address="a@b.com", subject="Hi", body_text="x") == "mid-2"
    ses.send_email.assert_called_once()
