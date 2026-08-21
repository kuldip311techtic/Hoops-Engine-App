"""Amazon SES adapter. Routes must not import boto3."""

from loguru import logger

from app.core.config import Settings, get_settings
from app.exceptions.base import AppError, ServiceUnavailableError


class SESClient:
    """Thin wrapper around boto3 SES ``send_email``."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Bind settings used for region, credentials, and from-address."""
        self._settings = settings or get_settings()

    def _client(self):
        """Build a boto3 SES client from settings."""
        import boto3

        kwargs: dict[str, str] = {"region_name": self._settings.aws_region}
        if self._settings.aws_access_key_id and self._settings.aws_secret_access_key:
            kwargs["aws_access_key_id"] = self._settings.aws_access_key_id
            kwargs["aws_secret_access_key"] = self._settings.aws_secret_access_key
        return boto3.client("ses", **kwargs)

    def send_email(self, *, to_address: str, subject: str, body_text: str) -> str:
        """Send a plaintext email and return the SES MessageId.

        Raises:
            ServiceUnavailableError: When SES_FROM_EMAIL is not configured.
            AppError: When the provider call fails.
        """
        from_address = self._settings.ses_from_email
        if not from_address:
            raise ServiceUnavailableError(
                "Email is not configured",
                code="EMAIL_NOT_CONFIGURED",
            )
        try:
            response = self._client().send_email(
                Source=from_address,
                Destination={"ToAddresses": [to_address]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Text": {"Data": body_text, "Charset": "UTF-8"}},
                },
            )
        except ServiceUnavailableError:
            raise
        except Exception as exc:
            logger.exception("ses_send_failed")
            raise AppError(
                "Failed to send email",
                code="EMAIL_SEND_FAILED",
                status_code=502,
            ) from exc
        return str(response.get("MessageId", ""))
