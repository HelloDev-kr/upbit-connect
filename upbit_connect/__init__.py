"""Upbit Connect - Modern Python library for Upbit Open API.

This package provides a complete, type-safe interface to the Upbit cryptocurrency
exchange API, including REST endpoints and WebSocket streaming.

Example:
    >>> from upbit_connect import AsyncUpbitClient
    >>> async with AsyncUpbitClient(access_key="...", secret_key="...") as client:
    ...     ticker = await client.quotation.get_ticker("KRW-BTC")
    ...     accounts = await client.exchange.get_accounts()
"""

__version__ = "0.1.0"

from upbit_connect.client import AsyncUpbitClient, UpbitClient
from upbit_connect.exceptions import (
    UpbitAPIError,
    UpbitAuthError,
    UpbitError,
    UpbitNetworkError,
    UpbitRateLimitError,
    UpbitValidationError,
)
from upbit_connect.models.exchange import OrderSide, OrderType
from upbit_connect.models.quotation import AskBid, ChangeType
from upbit_connect.websocket import UpbitWebSocket

__all__ = [
    "AskBid",
    "AsyncUpbitClient",
    "ChangeType",
    "OrderSide",
    "OrderType",
    "UpbitAPIError",
    "UpbitAuthError",
    "UpbitClient",
    "UpbitError",
    "UpbitNetworkError",
    "UpbitRateLimitError",
    "UpbitValidationError",
    "UpbitWebSocket",
    "__version__",
]
