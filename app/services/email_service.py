"""Email use-case wrapping the SES client."""

from app.clients.ses_client import SESClient


class EmailService:
    """Application-facing email API. Routes depend on this, not boto3."""

    def __init__(self, client: SESClient | None = None) -> None:
        """Inject or construct the SES adapter."""
        self._client = client or SESClient()

    def send_email(self, *, to_address: str, subject: str, body_text: str) -> str:
        """Send an email via SES and return the provider message id."""
        return self._client.send_email(
            to_address=to_address,
            subject=subject,
            body_text=body_text,
        )
