"""Typed application errors mapped to HTTP responses."""


class AppError(Exception):
    """Base application error with a UI-safe message and stable error code."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "APP_ERROR",
        status_code: int = 400,
        details: object | None = None,
    ) -> None:
        """Create an application error.

        Args:
            message: UI-safe message returned to the client.
            code: Stable machine-readable error code.
            status_code: HTTP status to emit.
            details: Optional field-level or structured details.
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class UnauthorizedError(AppError):
    """Raised when authentication fails or a token is invalid."""

    def __init__(
        self,
        message: str = "Not authenticated",
        *,
        code: str = "UNAUTHORIZED",
        details: object | None = None,
    ) -> None:
        """Create a 401 error."""
        super().__init__(message, code=code, status_code=401, details=details)


class ForbiddenError(AppError):
    """Raised when an authenticated principal lacks permission."""

    def __init__(
        self,
        message: str = "Access denied",
        *,
        code: str = "FORBIDDEN",
        details: object | None = None,
    ) -> None:
        """Create a 403 error."""
        super().__init__(message, code=code, status_code=403, details=details)


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    def __init__(
        self,
        message: str = "Resource not found",
        *,
        code: str = "NOT_FOUND",
        details: object | None = None,
    ) -> None:
        """Create a 404 error."""
        super().__init__(message, code=code, status_code=404, details=details)


class ConflictError(AppError):
    """Raised when a unique constraint or conflicting state is hit."""

    def __init__(
        self,
        message: str = "Resource already exists",
        *,
        code: str = "CONFLICT",
        details: object | None = None,
    ) -> None:
        """Create a 409 error."""
        super().__init__(message, code=code, status_code=409, details=details)


class ServiceUnavailableError(AppError):
    """Raised when a required dependency is unavailable."""

    def __init__(
        self,
        message: str = "Service unavailable",
        *,
        code: str = "SERVICE_UNAVAILABLE",
        details: object | None = None,
    ) -> None:
        """Create a 503 error."""
        super().__init__(message, code=code, status_code=503, details=details)
