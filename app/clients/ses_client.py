"""Amazon SES HTTP/SDK wrapper. Routes must never import boto3."""

from typing import Any

from loguru import logger

from app.core.config import Settings, get_settings
from app.exceptions import EmailDeliveryError, EmailNotConfiguredError


class SESClient:
    """Thin adapter around boto3 SES ``send_email``.

    Secrets and region come from Settings. The boto3 client is created lazily
    so unit tests can substitute ``_client`` without AWS credentials.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client: Any = None

    def _get_boto_client(self) -> Any:
        """Create (or reuse) the boto3 SES client."""
        if self._client is not None:
            return self._client
        try:
            import boto3
        except ImportError as exc:
            raise EmailNotConfiguredError(
                "Email delivery is not configured",
            ) from exc
        kwargs: dict[str, Any] = {"region_name": self._settings.aws_region}
        if self._settings.aws_access_key_id and self._settings.aws_secret_access_key:
            kwargs["aws_access_key_id"] = self._settings.aws_access_key_id
            kwargs["aws_secret_access_key"] = self._settings.aws_secret_access_key
        self._client = boto3.client("ses", **kwargs)
        return self._client

    def send_email(
        self,
        *,
        to_address: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
    ) -> str:
        """Send an email via Amazon SES.

        Returns:
            The SES ``MessageId``.

        Raises:
            EmailNotConfiguredError: Missing from-address or AWS configuration.
            EmailDeliveryError: SES API failure. Message is UI-safe.
        """
        if not self._settings.ses_from_email:
            raise EmailNotConfiguredError()
        destination = {"ToAddresses": [to_address]}
        body: dict[str, Any] = {"Html": {"Charset": "UTF-8", "Data": html_body}}
        if text_body:
            body["Text"] = {"Charset": "UTF-8", "Data": text_body}
        message: dict[str, Any] = {
            "Subject": {"Charset": "UTF-8", "Data": subject},
            "Body": body,
        }
        request: dict[str, Any] = {
            "Source": self._settings.ses_from_email,
            "Destination": destination,
            "Message": message,
        }
        if self._settings.ses_configuration_set:
            request["ConfigurationSetName"] = self._settings.ses_configuration_set
        try:
            response = self._get_boto_client().send_email(**request)
        except EmailNotConfiguredError:
            raise
        except Exception as exc:
            logger.opt(exception=exc).warning("ses_send_email_failed")
            raise EmailDeliveryError() from exc
        message_id = response.get("MessageId", "")
        logger.info("ses_send_email_ok message_id={}", message_id)
        return str(message_id)
