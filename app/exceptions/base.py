"""Custom domain/HTTP exceptions.

Do not name a class HTTPException — that would shadow FastAPI's type.
"""


class AppError(Exception):
    """Base application error mapped to a UI-safe HTTP response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        code: str,
        details: list[dict] | dict | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details


class UnauthorizedError(AppError):
    """Raised when authentication is missing or invalid."""

    def __init__(
        self,
        message: str = "Authentication required",
        *,
        code: str = "UNAUTHORIZED",
        details: list[dict] | dict | None = None,
    ) -> None:
        super().__init__(message, status_code=401, code=code, details=details)


class ForbiddenError(AppError):
    """Raised when the caller is authenticated but not allowed."""

    def __init__(
        self,
        message: str = "You do not have permission to perform this action",
        *,
        code: str = "FORBIDDEN",
        details: list[dict] | dict | None = None,
    ) -> None:
        super().__init__(message, status_code=403, code=code, details=details)


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    def __init__(
        self,
        message: str = "Resource not found",
        *,
        code: str = "NOT_FOUND",
        details: list[dict] | dict | None = None,
    ) -> None:
        super().__init__(message, status_code=404, code=code, details=details)


class ConflictError(AppError):
    """Raised when a unique constraint or state conflict occurs."""

    def __init__(
        self,
        message: str = "Resource already exists",
        *,
        code: str = "CONFLICT",
        details: list[dict] | dict | None = None,
    ) -> None:
        super().__init__(message, status_code=409, code=code, details=details)


class EmailDeliveryError(AppError):
    """Raised when Amazon SES fails to send a message."""

    def __init__(
        self,
        message: str = "Unable to send email at this time",
        *,
        code: str = "EMAIL_DELIVERY_FAILED",
        details: list[dict] | dict | None = None,
    ) -> None:
        super().__init__(message, status_code=502, code=code, details=details)


class EmailNotConfiguredError(AppError):
    """Raised when SES credentials or from-address are missing."""

    def __init__(
        self,
        message: str = "Email delivery is not configured",
        *,
        code: str = "EMAIL_NOT_CONFIGURED",
        details: list[dict] | dict | None = None,
    ) -> None:
        super().__init__(message, status_code=503, code=code, details=details)
