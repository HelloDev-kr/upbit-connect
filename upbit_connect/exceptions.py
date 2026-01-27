"""Exception hierarchy for the Upbit Connect library.

This module defines all custom exceptions used throughout the library to provide
clear error reporting and handling of Upbit API specific errors.
"""


class UpbitError(Exception):
    """Base exception for all Upbit Connect related errors.

    Args:
        message: A human-readable error description.
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class UpbitAPIError(UpbitError):
    """Exception raised for errors returned by the Upbit API.

    Attributes:
        status_code: The HTTP status code returned by the API.
        error_name: The error name returned by the API (if any).
        error_message: The detailed error message from the API.
    """

    def __init__(
        self,
        message: str,
        status_code: int,
        error_name: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Initializes UpbitAPIError.

        Args:
            message: Human-readable error description.
            status_code: HTTP status code.
            error_name: Error name from Upbit.
            error_message: Error message from Upbit.
        """
        super().__init__(message)
        self.status_code = status_code
        self.error_name = error_name
        self.error_message = error_message


class UpbitAuthError(UpbitError):
    """Exception raised for authentication or authorization failures (401, 403)."""

    pass


class UpbitRateLimitError(UpbitError):
    """Exception raised when API rate limits are exceeded (429).

    Attributes:
        retry_after: Seconds to wait before retrying.
    """

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        """Initializes UpbitRateLimitError.

        Args:
            message: Human-readable error description.
            retry_after: Optional wait time in seconds.
        """
        super().__init__(message)
        self.retry_after = retry_after


class UpbitValidationError(UpbitError):
    """Exception raised for client-side validation failures."""

    pass


class UpbitNetworkError(UpbitError):
    """Exception raised for network or connection related issues."""

    pass


def get_exception_for_status(status_code: int) -> type[UpbitError]:
    """Maps HTTP status codes to the appropriate UpbitError subclass.

    Args:
        status_code: The HTTP status code to map.

    Returns:
        The exception class corresponding to the status code.
    """
    if status_code in (401, 403):
        return UpbitAuthError
    if status_code == 429:  # noqa: PLR2004
        return UpbitRateLimitError
    if 400 <= status_code < 600:  # noqa: PLR2004
        return UpbitAPIError
    return UpbitError
