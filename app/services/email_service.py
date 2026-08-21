"""Email application service. Routes depend on this, never on SES/boto3."""

from app.clients.ses_client import SESClient
from app.core.config import Settings, get_settings
from app.exceptions import EmailNotConfiguredError


class EmailService:
    """Application-level email sender backed by Amazon SES."""

    def __init__(
        self,
        ses_client: SESClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._ses_client = ses_client or SESClient(self._settings)

    def send_email(
        self,
        *,
        to_address: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
    ) -> str:
        """Send an email if SES is configured.

        Returns:
            SES MessageId.

        Raises:
            EmailNotConfiguredError: SES is not configured.
            EmailDeliveryError: Provider failure (UI-safe message).
        """
        if not self._settings.ses_is_configured:
            raise EmailNotConfiguredError()
        return self._ses_client.send_email(
            to_address=to_address,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
        )
