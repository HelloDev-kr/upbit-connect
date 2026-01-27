"""Quotation Service for Upbit market data API endpoints.

This module provides both sync and async service classes for accessing
Upbit's public market data endpoints:
- Market list
- Candles (minute/day/week/month)
- Ticker (current prices)
- Orderbook (order book depth)
- Trades (recent trade history)

All responses are parsed into Pydantic models for type safety.
"""

from datetime import datetime
from typing import Literal

from upbit_connect._client_base import AsyncRequester, SyncRequester
from upbit_connect.models.quotation import (
    CandleDay,
    CandleMinute,
    CandleMonth,
    CandleWeek,
    Orderbook,
    Ticker,
    Trade,
)

MinuteUnit = Literal[1, 3, 5, 10, 15, 30, 60, 240]


class SyncQuotationService:
    """Synchronous service for Upbit Quotation (market data) API endpoints.

    Provides access to public market data including prices, candles,
    orderbook, and trade history. No authentication required.

    Attributes:
        client: Requester instance for making HTTP requests.
    """

    def __init__(self, client: SyncRequester) -> None:
        """Initialize the sync quotation service.

        Args:
            client: Requester instance for making HTTP requests.
        """
        self.client = client

    def get_markets(self, is_details: bool = False) -> list[dict[str, str | bool]]:
        """Get list of all available markets.

        Args:
            is_details: If True, include market warning info.

        Returns:
            List of market information dictionaries.
        """
        params = self.client._prepare_params(isDetails=is_details)
        response = self.client._get("/v1/market/all", params=params)
        data: list[dict[str, str | bool]] = response.json()
        return data

    def get_candles_minutes(
        self,
        market: str,
        unit: MinuteUnit = 1,
        to: datetime | None = None,
        count: int = 200,
    ) -> list[CandleMinute]:
        """Get minute candles for a market.

        Args:
            market: Market code (e.g., "KRW-BTC").
            unit: Candle interval in minutes (1, 3, 5, 10, 15, 30, 60, 240).
            to: Return candles before this datetime. If None, returns latest.
            count: Number of candles to return (max 200).

        Returns:
            List of minute candle data.
        """
        params = self.client._prepare_params(market=market, to=to, count=count)
        response = self.client._get(f"/v1/candles/minutes/{unit}", params=params)
        data = response.json()
        return [CandleMinute(**item) for item in data]

    def get_candles_days(
        self,
        market: str,
        to: datetime | None = None,
        count: int = 200,
        converting_price_unit: str | None = None,
    ) -> list[CandleDay]:
        """Get daily candles for a market.

        Args:
            market: Market code (e.g., "KRW-BTC").
            to: Return candles before this datetime. If None, returns latest.
            count: Number of candles to return (max 200).
            converting_price_unit: Currency for price conversion (e.g., "KRW").

        Returns:
            List of daily candle data.
        """
        params = self.client._prepare_params(
            market=market,
            to=to,
            count=count,
            convertingPriceUnit=converting_price_unit,
        )
        response = self.client._get("/v1/candles/days", params=params)
        data = response.json()
        return [CandleDay(**item) for item in data]

    def get_candles_weeks(
        self,
        market: str,
        to: datetime | None = None,
        count: int = 200,
    ) -> list[CandleWeek]:
        """Get weekly candles for a market.

        Args:
            market: Market code (e.g., "KRW-BTC").
            to: Return candles before this datetime. If None, returns latest.
            count: Number of candles to return (max 200).

        Returns:
            List of weekly candle data.
        """
        params = self.client._prepare_params(market=market, to=to, count=count)
        response = self.client._get("/v1/candles/weeks", params=params)
        data = response.json()
        return [CandleWeek(**item) for item in data]

    def get_candles_months(
        self,
        market: str,
        to: datetime | None = None,
        count: int = 200,
    ) -> list[CandleMonth]:
        """Get monthly candles for a market.

        Args:
            market: Market code (e.g., "KRW-BTC").
            to: Return candles before this datetime. If None, returns latest.
            count: Number of candles to return (max 200).

        Returns:
            List of monthly candle data.
        """
        params = self.client._prepare_params(market=market, to=to, count=count)
        response = self.client._get("/v1/candles/months", params=params)
        data = response.json()
        return [CandleMonth(**item) for item in data]

    def get_ticker(self, markets: str | list[str]) -> list[Ticker]:
        """Get current price ticker for one or more markets.

        Args:
            markets: Market code(s).

        Returns:
            List of ticker data for requested markets.
        """
        params = self.client._prepare_params(markets=markets)
        response = self.client._get("/v1/ticker", params=params)
        data = response.json()
        return [Ticker(**item) for item in data]

    def get_orderbook(self, markets: str | list[str]) -> list[Orderbook]:
        """Get orderbook (order book depth) for one or more markets.

        Args:
            markets: Market code(s).

        Returns:
            List of orderbook data for requested markets.
        """
        params = self.client._prepare_params(markets=markets)
        response = self.client._get("/v1/orderbook", params=params)
        data = response.json()
        return [Orderbook(**item) for item in data]

    def get_trades(
        self,
        market: str,
        to: str | None = None,
        count: int = 100,
        cursor: str | None = None,
        days_ago: int | None = None,
    ) -> list[Trade]:
        """Get recent trade history for a market.

        Args:
            market: Market code (e.g., "KRW-BTC").
            to: Return trades before this time.
            count: Number of trades to return (max 500, default 100).
            cursor: Pagination cursor from previous response.
            days_ago: Get trades from N days ago (0-7).

        Returns:
            List of recent trade data.
        """
        params = self.client._prepare_params(
            market=market, to=to, count=count, cursor=cursor, daysAgo=days_ago
        )
        response = self.client._get("/v1/trades/ticks", params=params)
        data = response.json()
        return [Trade(**item) for item in data]


class AsyncQuotationService:
    """Asynchronous service for Upbit Quotation (market data) API endpoints.

    Provides access to public market data including prices, candles,
    orderbook, and trade history. No authentication required.

    Attributes:
        client: Requester instance for making HTTP requests.
    """

    def __init__(self, client: AsyncRequester) -> None:
        """Initialize the async quotation service.

        Args:
            client: Requester instance for making HTTP requests.
        """
        self.client = client

    async def get_markets(self, is_details: bool = False) -> list[dict[str, str | bool]]:
        """Get list of all available markets.

        Args:
            is_details: If True, include market warning info.

        Returns:
            List of market information dictionaries.
        """
        params = self.client._prepare_params(isDetails=is_details)
        response = await self.client._get("/v1/market/all", params=params)
        data: list[dict[str, str | bool]] = response.json()
        return data

    async def get_candles_minutes(
        self,
        market: str,
        unit: MinuteUnit = 1,
        to: datetime | None = None,
        count: int = 200,
    ) -> list[CandleMinute]:
        """Get minute candles for a market.

        Args:
            market: Market code (e.g., "KRW-BTC").
            unit: Candle interval in minutes (1, 3, 5, 10, 15, 30, 60, 240).
            to: Return candles before this datetime. If None, returns latest.
            count: Number of candles to return (max 200).

        Returns:
            List of minute candle data.
        """
        params = self.client._prepare_params(market=market, to=to, count=count)
        response = await self.client._get(f"/v1/candles/minutes/{unit}", params=params)
        data = response.json()
        return [CandleMinute(**item) for item in data]

    async def get_candles_days(
        self,
        market: str,
        to: datetime | None = None,
        count: int = 200,
        converting_price_unit: str | None = None,
    ) -> list[CandleDay]:
        """Get daily candles for a market.

        Args:
            market: Market code (e.g., "KRW-BTC").
            to: Return candles before this datetime. If None, returns latest.
            count: Number of candles to return (max 200).
            converting_price_unit: Currency for price conversion (e.g., "KRW").

        Returns:
            List of daily candle data.
        """
        params = self.client._prepare_params(
            market=market,
            to=to,
            count=count,
            convertingPriceUnit=converting_price_unit,
        )
        response = await self.client._get("/v1/candles/days", params=params)
        data = response.json()
        return [CandleDay(**item) for item in data]

    async def get_candles_weeks(
        self,
        market: str,
        to: datetime | None = None,
        count: int = 200,
    ) -> list[CandleWeek]:
        """Get weekly candles for a market.

        Args:
            market: Market code (e.g., "KRW-BTC").
            to: Return candles before this datetime. If None, returns latest.
            count: Number of candles to return (max 200).

        Returns:
            List of weekly candle data.
        """
        params = self.client._prepare_params(market=market, to=to, count=count)
        response = await self.client._get("/v1/candles/weeks", params=params)
        data = response.json()
        return [CandleWeek(**item) for item in data]

    async def get_candles_months(
        self,
        market: str,
        to: datetime | None = None,
        count: int = 200,
    ) -> list[CandleMonth]:
        """Get monthly candles for a market.

        Args:
            market: Market code (e.g., "KRW-BTC").
            to: Return candles before this datetime. If None, returns latest.
            count: Number of candles to return (max 200).

        Returns:
            List of monthly candle data.
        """
        params = self.client._prepare_params(market=market, to=to, count=count)
        response = await self.client._get("/v1/candles/months", params=params)
        data = response.json()
        return [CandleMonth(**item) for item in data]

    async def get_ticker(self, markets: str | list[str]) -> list[Ticker]:
        """Get current price ticker for one or more markets.

        Args:
            markets: Market code(s).

        Returns:
            List of ticker data for requested markets.
        """
        params = self.client._prepare_params(markets=markets)
        response = await self.client._get("/v1/ticker", params=params)
        data = response.json()
        return [Ticker(**item) for item in data]

    async def get_orderbook(self, markets: str | list[str]) -> list[Orderbook]:
        """Get orderbook (order book depth) for one or more markets.

        Args:
            markets: Market code(s).

        Returns:
            List of orderbook data for requested markets.
        """
        params = self.client._prepare_params(markets=markets)
        response = await self.client._get("/v1/orderbook", params=params)
        data = response.json()
        return [Orderbook(**item) for item in data]

    async def get_trades(
        self,
        market: str,
        to: str | None = None,
        count: int = 100,
        cursor: str | None = None,
        days_ago: int | None = None,
    ) -> list[Trade]:
        """Get recent trade history for a market.

        Args:
            market: Market code (e.g., "KRW-BTC").
            to: Return trades before this time.
            count: Number of trades to return (max 500, default 100).
            cursor: Pagination cursor from previous response.
            days_ago: Get trades from N days ago (0-7).

        Returns:
            List of recent trade data.
        """
        params = self.client._prepare_params(
            market=market, to=to, count=count, cursor=cursor, daysAgo=days_ago
        )
        response = await self.client._get("/v1/trades/ticks", params=params)
        data = response.json()
        return [Trade(**item) for item in data]
