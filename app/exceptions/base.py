"""Application-specific exception classes."""

from typing import Any


class AppException(Exception):
    """Base application exception mapped to an HTTP response."""

    status_code: int = 400
    error_code: str = "APP_ERROR"

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.error_code
        self.details = details


class AuthenticationError(AppException):
    """Raised when authentication fails."""

    status_code = 401
    error_code = "AUTHENTICATION_FAILED"


class AuthorizationError(AppException):
    """Raised when the caller lacks permission."""

    status_code = 403
    error_code = "AUTHORIZATION_FAILED"


class NotFoundError(AppException):
    """Raised when a requested resource is not found."""

    status_code = 404
    error_code = "NOT_FOUND"


class ConflictError(AppException):
    """Raised when a resource conflict occurs."""

    status_code = 409
    error_code = "CONFLICT"


class ValidationAppError(AppException):
    """Raised for domain-level validation failures."""

    status_code = 422
    error_code = "VALIDATION_ERROR"
