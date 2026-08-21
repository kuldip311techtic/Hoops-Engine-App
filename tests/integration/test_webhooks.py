"""Webhook HTTP tests."""

from unittest.mock import MagicMock

from app.api.v1.endpoints.webhooks import get_webhook_service
from app.schemas.webhook import WebhookAckData, WebhookAckResponse
from app.services.webhook_service import WebhookService


async def test_auth0_webhook_accepted(app, client) -> None:
    """POST /api/v1/webhooks/auth0 returns the success envelope."""
    service = MagicMock(spec=WebhookService)
    service.handle_auth0.return_value = WebhookAckResponse(
        success=True,
        message="Auth0 event accepted",
        data=WebhookAckData(
            accepted=True,
            type="scim.user.updated",
            email="admin@example.com",
            description="User password changed",
            message="Auth0 event accepted",
            error=None,
        ),
    )
    app.dependency_overrides[get_webhook_service] = lambda: service
    try:
        response = await client.post(
            "/api/v1/webhooks/auth0",
            json={
                "type": "scim.user.updated",
                "email": "admin@example.com",
                "description": "User password changed",
            },
            headers={"X-Webhook-Signature": "test"},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["error"] is None
    assert body["data"]["email"] == "admin@example.com"
    service.handle_auth0.assert_called_once()
