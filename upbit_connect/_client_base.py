"""Base HTTP client functionality for Upbit API.

This module provides shared HTTP logic for both sync and async clients:
- Integration with auth module for JWT header injection
- Integration with rate limiter
- Error response handling and exception mapping
- Support for both httpx.Client and httpx.AsyncClient
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

import httpx

from upbit_connect.auth import generate_jwt_token
from upbit_connect.exceptions import (
    UpbitAPIError,
    UpbitAuthError,
    UpbitNetworkError,
    UpbitRateLimitError,
    UpbitValidationError,
    get_exception_for_status,
)
from upbit_connect.limiter import RateLimiter


@runtime_checkable
class SyncRequester(Protocol):
    """Protocol for synchronous request execution."""

    def _get(self, path: str, params: dict[str, Any] | None = None) -> httpx.Response: ...

    def _post(self, path: str, body: dict[str, Any] | None = None) -> httpx.Response: ...

    def _delete(self, path: str, params: dict[str, Any] | None = None) -> httpx.Response: ...

    def _prepare_params(self, **kwargs: Any) -> dict[str, Any]: ...

    def _validate_uuid_identifier(
        self,
        uuid: str | None = None,
        identifier: str | None = None,
    ) -> None: ...


@runtime_checkable
class AsyncRequester(Protocol):
    """Protocol for asynchronous request execution."""

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> httpx.Response: ...

    async def _post(self, path: str, body: dict[str, Any] | None = None) -> httpx.Response: ...

    async def _delete(self, path: str, params: dict[str, Any] | None = None) -> httpx.Response: ...

    def _prepare_params(self, **kwargs: Any) -> dict[str, Any]: ...

    def _validate_uuid_identifier(
        self,
        uuid: str | None = None,
        identifier: str | None = None,
    ) -> None: ...


class BaseClient:
    """Base client with shared HTTP logic.

    This class provides common functionality for both sync and async clients:
    - Request header building with optional JWT authentication
    - Rate limiter management for quotation and exchange endpoints
    - Error response parsing and exception mapping
    - Request parameter and body preparation helpers

    Attributes:
        base_url: Upbit API base URL.
        access_key: API access key (optional for public endpoints).
        secret_key: API secret key (optional for public endpoints).
        quotation_limiter: Rate limiter for market data endpoints.
        exchange_limiter: Rate limiter for trading operation endpoints.
    """

    BASE_URL = "https://api.upbit.com"

    _EXCHANGE_PREFIXES = (
        "/v1/orders",
        "/v1/order",
        "/v1/accounts",
        "/v1/withdraws",
        "/v1/withdraw",
        "/v1/deposits",
        "/v1/deposit",
    )

    def __init__(
        self,
        access_key: str | None = None,
        secret_key: str | None = None,
    ) -> None:
        """Initialize base client.

        Args:
            access_key: Upbit API access key (optional for public endpoints).
            secret_key: Upbit API secret key (optional for public endpoints).
        """
        self.base_url = self.BASE_URL
        self.access_key = access_key
        self.secret_key = secret_key
        self.quotation_limiter = RateLimiter("quotation", max_requests=30)
        self.exchange_limiter = RateLimiter("exchange", max_requests=8)

    def _build_headers(
        self,
        query_params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        """Build request headers with auth if credentials provided.

        Args:
            query_params: Optional query parameters for JWT hash.
            body: Optional request body for JWT hash.

        Returns:
            Dictionary of HTTP headers.
        """
        headers = {"Accept": "application/json"}

        if self.access_key and self.secret_key:
            token = generate_jwt_token(
                self.access_key,
                self.secret_key,
                query_params,
                body,
            )
            headers["Authorization"] = f"Bearer {token}"

        return headers

    def _get_limiter_for_path(self, path: str) -> RateLimiter:
        """Get the appropriate rate limiter based on endpoint path.

        Args:
            path: API endpoint path (e.g., "/v1/orders").

        Returns:
            The appropriate rate limiter for the endpoint.
        """
        for prefix in self._EXCHANGE_PREFIXES:
            if path.startswith(prefix):
                return self.exchange_limiter
        return self.quotation_limiter

    def _handle_error_response(self, response: httpx.Response) -> None:
        """Parse error response and raise appropriate exception.

        Parses the error details from the response body and raises the
        appropriate exception based on the HTTP status code.

        Args:
            response: The HTTP response to check for errors.

        Raises:
            UpbitAuthError: For 401/403 authentication errors.
            UpbitRateLimitError: For 429 rate limit errors.
            UpbitAPIError: For other 4xx/5xx API errors.
        """
        if response.is_success:
            return

        error_name: str | None = None
        error_message: str | None = None

        try:
            error_data = response.json()
            error_info = error_data.get("error", {})
            if isinstance(error_info, dict):
                error_name = error_info.get("name")
                error_message = error_info.get("message")
        except Exception:
            error_message = response.text or None

        exc_class = get_exception_for_status(response.status_code)

        message_text = error_message or f"HTTP {response.status_code}"

        if exc_class is UpbitRateLimitError:
            retry_after_header = response.headers.get("Retry-After")
            retry_after: float | None = None
            if retry_after_header:
                try:
                    retry_after = float(retry_after_header)
                except ValueError:
                    pass
            raise UpbitRateLimitError(
                f"Rate limit exceeded: {message_text}",
                retry_after=retry_after,
            )
        elif exc_class is UpbitAPIError:
            raise UpbitAPIError(
                f"API error: {message_text}",
                status_code=response.status_code,
                error_name=error_name,
                error_message=error_message,
            )
        elif exc_class is UpbitAuthError:
            raise UpbitAuthError(f"Authentication error: {message_text}")
        else:
            raise exc_class(f"Upbit error: {message_text}")

    def _update_limiter_from_response(
        self,
        response: httpx.Response,
        path: str,
    ) -> None:
        """Update rate limiter state from response headers.

        Args:
            response: The HTTP response containing rate limit headers.
            path: API endpoint path to determine which limiter to update.
        """
        limiter = self._get_limiter_for_path(path)
        headers_dict: dict[str, str] = dict(response.headers)
        limiter.update_from_headers(headers_dict)

    def _prepare_params(self, **kwargs: Any) -> dict[str, Any]:
        """Prepare request parameters/body by filtering None and converting types.

        Args:
            **kwargs: Parameters to prepare.

        Returns:
            Dictionary of prepared parameters.
        """
        params: dict[str, Any] = {}
        for k, v in kwargs.items():
            if v is None:
                continue
            if isinstance(v, datetime):
                params[k] = v.isoformat()
            elif isinstance(v, list):
                if k.endswith("[]"):
                    params[k] = v
                else:
                    params[k] = ",".join(map(str, v))
            elif isinstance(v, bool):
                params[k] = str(v).lower()
            elif isinstance(v, Decimal):
                params[k] = str(v)
            else:
                params[k] = v
        return params

    def _validate_uuid_identifier(
        self,
        uuid: str | None = None,
        identifier: str | None = None,
    ) -> None:
        """Validate that either uuid or identifier is provided.

        Args:
            uuid: Order/Deposit/Withdrawal UUID.
            identifier: Client-provided identifier.

        Raises:
            UpbitValidationError: If neither uuid nor identifier is provided.
        """
        if uuid is None and identifier is None:
            raise UpbitValidationError("Either uuid or identifier must be provided")

    def _wrap_network_error(self, error: Exception) -> UpbitNetworkError:
        """Wrap network-related exceptions in UpbitNetworkError.

        Args:
            error: The original network exception.

        Returns:
            UpbitNetworkError wrapping the original error.
        """
        if isinstance(error, httpx.ConnectError):
            return UpbitNetworkError(f"Connection failed: {error}")
        elif isinstance(error, httpx.TimeoutException):
            return UpbitNetworkError(f"Request timed out: {error}")
        elif isinstance(error, httpx.NetworkError):
            return UpbitNetworkError(f"Network error: {error}")
        else:
            return UpbitNetworkError(f"Unexpected network error: {error}")
