"""Authentication business logic."""

from app.core.config import get_settings
from app.core.logging import logger
from app.core.security import create_access_token, verify_password
from app.exceptions.base import AuthenticationError
from app.repositories.super_admin_repository import SuperAdminRepository
from app.schemas.auth import LoginData, LoginResponse


class AuthService:
    """Service for Super Admin authentication workflows."""

    def __init__(self, repository: SuperAdminRepository) -> None:
        """Initialize with a SuperAdmin repository."""
        self._repository = repository

    async def login_super_admin(self, email: str, password: str) -> LoginResponse:
        """Authenticate Super Admin credentials and return a JWT access token."""
        admin = await self._repository.get_by_email(email)
        if (
            admin is None
            or not admin.is_active
            or not verify_password(password, admin.hashed_password)
        ):
            logger.warning("Failed Super Admin login attempt for email={}", email)
            raise AuthenticationError(
                message="Invalid email or password.",
                error_code="AUTHENTICATION_FAILED",
            )

        settings = get_settings()
        token = create_access_token(
            subject=str(admin.id),
            claims={"email": admin.email, "role": "super_admin"},
        )
        expires_in = settings.access_token_expire_minutes * 60
        logger.info("Super Admin login successful for email={}", admin.email)

        return LoginResponse(
            success=True,
            message="Login successful.",
            description="Super Admin authenticated. Redirect to dashboard.",
            token=token,
            email=admin.email,
            data=LoginData(
                token=token,
                token_type="bearer",
                expires_in=expires_in,
                email=admin.email,
            ),
        )
