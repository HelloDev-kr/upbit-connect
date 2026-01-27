"""Main Upbit API client classes.

This module provides the primary client interfaces for interacting with
the Upbit REST API:

- UpbitClient: Synchronous client for blocking operations
- AsyncUpbitClient: Asynchronous client for async/await operations

Both clients integrate quotation (market data) and exchange (trading)
services with context manager support for proper resource cleanup.

Example (sync):
    >>> with UpbitClient(access_key="...", secret_key="...") as client:
    ...     accounts = client.exchange.get_accounts()
    ...     ticker = client.quotation.get_ticker("KRW-BTC")

Example (async):
    >>> async with AsyncUpbitClient(access_key="...", secret_key="...") as client:
    ...     accounts = await client.exchange.get_accounts()
    ...     ticker = await client.quotation.get_ticker("KRW-BTC")
"""

from typing import Any

import httpx

from upbit_connect._client_base import BaseClient
from upbit_connect.services.deposit import AsyncDepositService, DepositService
from upbit_connect.services.exchange import AsyncExchangeService, ExchangeService
from upbit_connect.services.quotation import AsyncQuotationService, SyncQuotationService
from upbit_connect.services.withdrawal import AsyncWithdrawalService, WithdrawalService


class UpbitClient(BaseClient):
    """Synchronous Upbit API client.

    Provides access to both quotation (market data) and exchange (trading)
    services through a unified interface. Supports context manager protocol
    for automatic resource cleanup.

    Example:
        >>> with UpbitClient(access_key="...", secret_key="...") as client:
        ...     accounts = client.exchange.get_accounts()
        ...     ticker = client.quotation.get_ticker("KRW-BTC")

    Attributes:
        quotation: Quotation (market data) service for prices, candles, etc.
        exchange: Exchange (trading) service for orders, accounts, etc.
        deposit: Deposit service for managing deposits.
        withdrawal: Withdrawal service for managing withdrawals.
    """

    quotation: SyncQuotationService
    exchange: ExchangeService
    deposit: DepositService
    withdrawal: WithdrawalService

    def __init__(
        self,
        access_key: str | None = None,
        secret_key: str | None = None,
    ) -> None:
        """Initialize the synchronous Upbit client.

        Args:
            access_key: Upbit API access key (required for exchange endpoints).
            secret_key: Upbit API secret key (required for exchange endpoints).
        """
        super().__init__(access_key, secret_key)
        self._http_client = httpx.Client(base_url=self.base_url)
        self.quotation = SyncQuotationService(self)
        self.exchange = ExchangeService(self)
        self.deposit = DepositService(self)
        self.withdrawal = WithdrawalService(self)

    def __enter__(self) -> "UpbitClient":
        """Enter context manager.

        Returns:
            The client instance.
        """
        return self

    def __exit__(self, *args: object) -> None:
        """Exit context manager and close HTTP client."""
        self.close()

    def close(self) -> None:
        """Close the HTTP client and release resources."""
        self._http_client.close()

    def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Make a GET request with authentication and rate limiting.

        Args:
            path: API endpoint path (e.g., "/v1/accounts").
            params: Optional query parameters.

        Returns:
            HTTP response object.

        Raises:
            UpbitAPIError: If the API returns an error response.
            UpbitAuthError: If authentication fails.
            UpbitRateLimitError: If rate limit is exceeded.
        """
        headers = self._build_headers(params, None)
        response = self._http_client.get(path, params=params, headers=headers)

        self._update_limiter_from_response(response, path)
        self._handle_error_response(response)

        return response

    def _post(
        self,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Make a POST request with authentication and rate limiting.

        Args:
            path: API endpoint path (e.g., "/v1/orders").
            body: Optional request body (JSON).

        Returns:
            HTTP response object.

        Raises:
            UpbitAPIError: If the API returns an error response.
            UpbitAuthError: If authentication fails.
            UpbitRateLimitError: If rate limit is exceeded.
        """
        headers = self._build_headers(None, body)
        response = self._http_client.post(path, json=body, headers=headers)

        self._update_limiter_from_response(response, path)
        self._handle_error_response(response)

        return response

    def _delete(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Make a DELETE request with authentication and rate limiting.

        Args:
            path: API endpoint path (e.g., "/v1/order").
            params: Optional query parameters.

        Returns:
            HTTP response object.

        Raises:
            UpbitAPIError: If the API returns an error response.
            UpbitAuthError: If authentication fails.
            UpbitRateLimitError: If rate limit is exceeded.
        """
        headers = self._build_headers(params, None)
        response = self._http_client.delete(path, params=params, headers=headers)

        self._update_limiter_from_response(response, path)
        self._handle_error_response(response)

        return response


class AsyncUpbitClient(BaseClient):
    """Asynchronous Upbit API client.

    Provides access to both quotation (market data) and exchange (trading)
    services through a unified interface. Supports async context manager
    protocol for automatic resource cleanup.

    Example:
        >>> async with AsyncUpbitClient(access_key="...", secret_key="...") as client:
        ...     accounts = await client.exchange.get_accounts()
        ...     ticker = await client.quotation.get_ticker("KRW-BTC")

    Attributes:
        quotation: Async quotation (market data) service for prices, candles, etc.
        exchange: Async exchange (trading) service for orders, accounts, etc.
    """

    quotation: AsyncQuotationService
    exchange: AsyncExchangeService
    deposit: AsyncDepositService
    withdrawal: AsyncWithdrawalService

    def __init__(
        self,
        access_key: str | None = None,
        secret_key: str | None = None,
    ) -> None:
        """Initialize the asynchronous Upbit client.

        Args:
            access_key: Upbit API access key (required for exchange endpoints).
            secret_key: Upbit API secret key (required for exchange endpoints).
        """
        super().__init__(access_key, secret_key)
        self._http_client = httpx.AsyncClient(base_url=self.base_url)
        self.quotation = AsyncQuotationService(self)
        self.exchange = AsyncExchangeService(self)
        self.deposit = AsyncDepositService(self)
        self.withdrawal = AsyncWithdrawalService(self)

    async def __aenter__(self) -> "AsyncUpbitClient":
        """Enter async context manager.

        Returns:
            The client instance.
        """
        return self

    async def __aexit__(self, *args: object) -> None:
        """Exit async context manager and close HTTP client."""
        await self.close()

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        await self._http_client.aclose()

    async def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Make an async GET request with authentication and rate limiting.

        Args:
            path: API endpoint path (e.g., "/v1/accounts").
            params: Optional query parameters.

        Returns:
            HTTP response object.

        Raises:
            UpbitAPIError: If the API returns an error response.
            UpbitAuthError: If authentication fails.
            UpbitRateLimitError: If rate limit is exceeded.
        """
        limiter = self._get_limiter_for_path(path)
        await limiter.wait_if_needed()

        headers = self._build_headers(params, None)
        response = await self._http_client.get(path, params=params, headers=headers)

        self._update_limiter_from_response(response, path)
        self._handle_error_response(response)

        return response

    async def _post(
        self,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Make an async POST request with authentication and rate limiting.

        Args:
            path: API endpoint path (e.g., "/v1/orders").
            body: Optional request body (JSON).

        Returns:
            HTTP response object.

        Raises:
            UpbitAPIError: If the API returns an error response.
            UpbitAuthError: If authentication fails.
            UpbitRateLimitError: If rate limit is exceeded.
        """
        limiter = self._get_limiter_for_path(path)
        await limiter.wait_if_needed()

        headers = self._build_headers(None, body)
        response = await self._http_client.post(path, json=body, headers=headers)

        self._update_limiter_from_response(response, path)
        self._handle_error_response(response)

        return response

    async def _delete(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Make an async DELETE request with authentication and rate limiting.

        Args:
            path: API endpoint path (e.g., "/v1/order").
            params: Optional query parameters.

        Returns:
            HTTP response object.

        Raises:
            UpbitAPIError: If the API returns an error response.
            UpbitAuthError: If authentication fails.
            UpbitRateLimitError: If rate limit is exceeded.
        """
        limiter = self._get_limiter_for_path(path)
        await limiter.wait_if_needed()

        headers = self._build_headers(params, None)
        response = await self._http_client.delete(path, params=params, headers=headers)

        self._update_limiter_from_response(response, path)
        self._handle_error_response(response)

        return response
