"""Tests for quotation service endpoints.

This module tests SyncQuotationService and AsyncQuotationService using respx
to mock HTTP responses from the Upbit API.
"""

from datetime import datetime
from decimal import Decimal

import httpx
import pytest
import respx

from upbit_connect.client import AsyncUpbitClient, UpbitClient
from upbit_connect.exceptions import UpbitAPIError, UpbitAuthError, UpbitRateLimitError
from upbit_connect.models.quotation import (
    CandleDay,
    CandleMinute,
    CandleMonth,
    CandleWeek,
    Orderbook,
    Ticker,
    Trade,
)

BASE_URL = "https://api.upbit.com"


# --- Mock Response Data ---

MOCK_MARKETS = [
    {
        "market": "KRW-BTC",
        "korean_name": "비트코인",
        "english_name": "Bitcoin",
    },
    {
        "market": "KRW-ETH",
        "korean_name": "이더리움",
        "english_name": "Ethereum",
    },
]

MOCK_MARKETS_WITH_DETAILS = [
    {
        "market": "KRW-BTC",
        "korean_name": "비트코인",
        "english_name": "Bitcoin",
        "market_warning": "NONE",
    },
    {
        "market": "KRW-ETH",
        "korean_name": "이더리움",
        "english_name": "Ethereum",
        "market_warning": "CAUTION",
    },
]

MOCK_CANDLE_MINUTE = [
    {
        "market": "KRW-BTC",
        "candle_date_time_utc": "2024-01-27T12:00:00",
        "candle_date_time_kst": "2024-01-27T21:00:00",
        "opening_price": 50000000.0,
        "high_price": 50100000.0,
        "low_price": 49900000.0,
        "trade_price": 50050000.0,
        "timestamp": "2024-01-27T12:00:59",
        "candle_acc_trade_price": 1000000000.0,
        "candle_acc_trade_volume": 20.5,
        "unit": 1,
    }
]

MOCK_CANDLE_DAY = [
    {
        "market": "KRW-BTC",
        "candle_date_time_utc": "2024-01-27T00:00:00",
        "candle_date_time_kst": "2024-01-27T09:00:00",
        "opening_price": 49000000.0,
        "high_price": 51000000.0,
        "low_price": 48500000.0,
        "trade_price": 50500000.0,
        "timestamp": "2024-01-27T23:59:59",
        "candle_acc_trade_price": 50000000000.0,
        "candle_acc_trade_volume": 1000.0,
        "prev_closing_price": 49000000.0,
        "change_price": 1500000.0,
        "change_rate": 0.0306,
        "converted_trade_price": None,
    }
]

MOCK_CANDLE_WEEK = [
    {
        "market": "KRW-BTC",
        "candle_date_time_utc": "2024-01-22T00:00:00",
        "candle_date_time_kst": "2024-01-22T09:00:00",
        "opening_price": 48000000.0,
        "high_price": 52000000.0,
        "low_price": 47000000.0,
        "trade_price": 51000000.0,
        "timestamp": "2024-01-27T23:59:59",
        "candle_acc_trade_price": 200000000000.0,
        "candle_acc_trade_volume": 4000.0,
        "first_day_of_period": "2024-01-22",
    }
]

MOCK_CANDLE_MONTH = [
    {
        "market": "KRW-BTC",
        "candle_date_time_utc": "2024-01-01T00:00:00",
        "candle_date_time_kst": "2024-01-01T09:00:00",
        "opening_price": 45000000.0,
        "high_price": 55000000.0,
        "low_price": 43000000.0,
        "trade_price": 52000000.0,
        "timestamp": "2024-01-27T23:59:59",
        "candle_acc_trade_price": 800000000000.0,
        "candle_acc_trade_volume": 16000.0,
        "first_day_of_period": "2024-01-01",
    }
]

MOCK_TICKER = [
    {
        "market": "KRW-BTC",
        "trade_date": "20240127",
        "trade_time": "235959",
        "trade_date_kst": "20240128",
        "trade_time_kst": "085959",
        "trade_timestamp": 1706400000000,
        "opening_price": 49000000.0,
        "high_price": 51000000.0,
        "low_price": 48500000.0,
        "trade_price": 50500000.0,
        "prev_closing_price": 49000000.0,
        "change": "RISE",
        "change_price": 1500000.0,
        "change_rate": 0.0306122448979592,
        "signed_change_price": 1500000.0,
        "signed_change_rate": 0.0306122448979592,
        "trade_volume": 0.5,
        "acc_trade_price": 50000000000.0,
        "acc_trade_price_24h": 75000000000.0,
        "acc_trade_volume": 1000.0,
        "acc_trade_volume_24h": 1500.0,
        "highest_52_week_price": 70000000.0,
        "highest_52_week_date": "2024-03-14",
        "lowest_52_week_price": 25000000.0,
        "lowest_52_week_date": "2023-09-11",
        "timestamp": 1706400000000,
    }
]

MOCK_ORDERBOOK = [
    {
        "market": "KRW-BTC",
        "timestamp": 1706400000000,
        "total_ask_size": 100.5,
        "total_bid_size": 200.3,
        "orderbook_units": [
            {
                "ask_price": 50100000.0,
                "bid_price": 50000000.0,
                "ask_size": 10.5,
                "bid_size": 20.3,
            },
            {
                "ask_price": 50200000.0,
                "bid_price": 49900000.0,
                "ask_size": 15.0,
                "bid_size": 25.0,
            },
        ],
    }
]

MOCK_TRADES = [
    {
        "market": "KRW-BTC",
        "trade_date_utc": "2024-01-27",
        "trade_time_utc": "23:59:59",
        "timestamp": 1706400000000,
        "trade_price": 50500000.0,
        "trade_volume": 0.001,
        "prev_closing_price": 49000000.0,
        "change_price": 1500000.0,
        "ask_bid": "BID",
        "sequential_id": 123456789,
    },
    {
        "market": "KRW-BTC",
        "trade_date_utc": "2024-01-27",
        "trade_time_utc": "23:59:58",
        "timestamp": 1706399999000,
        "trade_price": 50490000.0,
        "trade_volume": 0.002,
        "prev_closing_price": 49000000.0,
        "change_price": 1490000.0,
        "ask_bid": "ASK",
        "sequential_id": 123456788,
    },
]


# --- Sync Service Tests ---


class TestSyncQuotationService:
    """Tests for synchronous quotation service."""

    @respx.mock
    def test_get_markets(self) -> None:
        """Test get_markets returns list of markets."""
        respx.get(f"{BASE_URL}/v1/market/all").mock(
            return_value=httpx.Response(200, json=MOCK_MARKETS)
        )

        with UpbitClient() as client:
            service = client.quotation
            result = service.get_markets()

        assert len(result) == 2
        assert result[0]["market"] == "KRW-BTC"
        assert result[1]["market"] == "KRW-ETH"

    @respx.mock
    def test_get_markets_with_details(self) -> None:
        """Test get_markets with is_details=True includes market_warning."""
        respx.get(f"{BASE_URL}/v1/market/all").mock(
            return_value=httpx.Response(200, json=MOCK_MARKETS_WITH_DETAILS)
        )

        with UpbitClient() as client:
            service = client.quotation
            result = service.get_markets(is_details=True)

        assert len(result) == 2
        assert "market_warning" in result[0]
        assert result[0]["market_warning"] == "NONE"
        assert result[1]["market_warning"] == "CAUTION"

    @respx.mock
    def test_get_candles_minutes_all_units(self) -> None:
        """Test get_candles_minutes works for all valid unit values."""
        valid_units = [1, 3, 5, 10, 15, 30, 60, 240]

        for unit in valid_units:
            mock_data = MOCK_CANDLE_MINUTE.copy()
            mock_data[0]["unit"] = unit
            respx.get(f"{BASE_URL}/v1/candles/minutes/{unit}").mock(
                return_value=httpx.Response(200, json=mock_data)
            )

        with UpbitClient() as client:
            service = client.quotation

            for unit in valid_units:
                result = service.get_candles_minutes("KRW-BTC", unit=unit)  # type: ignore[arg-type]
                assert len(result) == 1
                assert isinstance(result[0], CandleMinute)
                assert result[0].market == "KRW-BTC"

    @respx.mock
    def test_get_candles_minutes_with_params(self) -> None:
        """Test get_candles_minutes with to and count parameters."""
        respx.get(f"{BASE_URL}/v1/candles/minutes/1").mock(
            return_value=httpx.Response(200, json=MOCK_CANDLE_MINUTE)
        )

        with UpbitClient() as client:
            service = client.quotation
            to_datetime = datetime(2024, 1, 27, 12, 0, 0)
            result = service.get_candles_minutes("KRW-BTC", unit=1, to=to_datetime, count=100)

        assert len(result) == 1
        assert isinstance(result[0], CandleMinute)

    @respx.mock
    def test_get_candles_days(self) -> None:
        """Test get_candles_days returns daily candles."""
        respx.get(f"{BASE_URL}/v1/candles/days").mock(
            return_value=httpx.Response(200, json=MOCK_CANDLE_DAY)
        )

        with UpbitClient() as client:
            service = client.quotation
            result = service.get_candles_days("KRW-BTC")

        assert len(result) == 1
        assert isinstance(result[0], CandleDay)
        assert result[0].market == "KRW-BTC"
        assert result[0].prev_closing_price == Decimal("49000000")
        assert result[0].change_rate == Decimal("0.0306")

    @respx.mock
    def test_get_candles_weeks(self) -> None:
        """Test get_candles_weeks returns weekly candles."""
        respx.get(f"{BASE_URL}/v1/candles/weeks").mock(
            return_value=httpx.Response(200, json=MOCK_CANDLE_WEEK)
        )

        with UpbitClient() as client:
            service = client.quotation
            result = service.get_candles_weeks("KRW-BTC")

        assert len(result) == 1
        assert isinstance(result[0], CandleWeek)
        assert result[0].first_day_of_period == "2024-01-22"

    @respx.mock
    def test_get_candles_months(self) -> None:
        """Test get_candles_months returns monthly candles."""
        respx.get(f"{BASE_URL}/v1/candles/months").mock(
            return_value=httpx.Response(200, json=MOCK_CANDLE_MONTH)
        )

        with UpbitClient() as client:
            service = client.quotation
            result = service.get_candles_months("KRW-BTC")

        assert len(result) == 1
        assert isinstance(result[0], CandleMonth)
        assert result[0].first_day_of_period == "2024-01-01"

    @respx.mock
    def test_get_ticker_single_market(self) -> None:
        """Test get_ticker with single market string."""
        respx.get(f"{BASE_URL}/v1/ticker").mock(return_value=httpx.Response(200, json=MOCK_TICKER))

        with UpbitClient() as client:
            service = client.quotation
            result = service.get_ticker("KRW-BTC")

        assert len(result) == 1
        assert isinstance(result[0], Ticker)
        assert result[0].market == "KRW-BTC"
        assert result[0].trade_price == Decimal("50500000")

    @respx.mock
    def test_get_ticker_multiple_markets(self) -> None:
        """Test get_ticker with multiple markets as list."""
        mock_tickers = MOCK_TICKER.copy()
        mock_tickers.append({**MOCK_TICKER[0], "market": "KRW-ETH"})
        respx.get(f"{BASE_URL}/v1/ticker").mock(return_value=httpx.Response(200, json=mock_tickers))

        with UpbitClient() as client:
            service = client.quotation
            result = service.get_ticker(["KRW-BTC", "KRW-ETH"])

        assert len(result) == 2
        assert all(isinstance(t, Ticker) for t in result)

    @respx.mock
    def test_get_orderbook(self) -> None:
        """Test get_orderbook returns orderbook data."""
        respx.get(f"{BASE_URL}/v1/orderbook").mock(
            return_value=httpx.Response(200, json=MOCK_ORDERBOOK)
        )

        with UpbitClient() as client:
            service = client.quotation
            result = service.get_orderbook("KRW-BTC")

        assert len(result) == 1
        assert isinstance(result[0], Orderbook)
        assert result[0].market == "KRW-BTC"
        assert len(result[0].orderbook_units) == 2
        assert result[0].orderbook_units[0].ask_price == Decimal("50100000")

    @respx.mock
    def test_get_orderbook_multiple_markets(self) -> None:
        """Test get_orderbook with multiple markets."""
        mock_orderbooks = MOCK_ORDERBOOK.copy()
        mock_orderbooks.append({**MOCK_ORDERBOOK[0], "market": "KRW-ETH"})
        respx.get(f"{BASE_URL}/v1/orderbook").mock(
            return_value=httpx.Response(200, json=mock_orderbooks)
        )

        with UpbitClient() as client:
            service = client.quotation
            result = service.get_orderbook(["KRW-BTC", "KRW-ETH"])

        assert len(result) == 2

    @respx.mock
    def test_get_trades(self) -> None:
        """Test get_trades returns recent trades."""
        respx.get(f"{BASE_URL}/v1/trades/ticks").mock(
            return_value=httpx.Response(200, json=MOCK_TRADES)
        )

        with UpbitClient() as client:
            service = client.quotation
            result = service.get_trades("KRW-BTC")

        assert len(result) == 2
        assert all(isinstance(t, Trade) for t in result)
        assert result[0].trade_price == Decimal("50500000")
        assert result[0].ask_bid.value == "BID"
        assert result[1].ask_bid.value == "ASK"

    @respx.mock
    def test_get_trades_with_params(self) -> None:
        """Test get_trades with various parameters."""
        respx.get(f"{BASE_URL}/v1/trades/ticks").mock(
            return_value=httpx.Response(200, json=MOCK_TRADES)
        )

        with UpbitClient() as client:
            service = client.quotation
            result = service.get_trades(
                market="KRW-BTC",
                to="23:59:59",
                count=50,
                cursor="some_cursor",
                days_ago=1,
            )

        assert len(result) == 2

    @respx.mock
    def test_model_parsing_decimal_precision(self) -> None:
        """Test that all Decimal fields maintain precision."""
        respx.get(f"{BASE_URL}/v1/ticker").mock(return_value=httpx.Response(200, json=MOCK_TICKER))

        with UpbitClient() as client:
            service = client.quotation
            result = service.get_ticker("KRW-BTC")

        ticker = result[0]
        # Verify Decimal types and precision
        assert isinstance(ticker.trade_price, Decimal)
        assert isinstance(ticker.change_rate, Decimal)
        assert ticker.change_rate == Decimal("0.0306122448979592")

    @respx.mock
    def test_model_parsing_datetime(self) -> None:
        """Test that timestamp fields are converted to datetime."""
        respx.get(f"{BASE_URL}/v1/ticker").mock(return_value=httpx.Response(200, json=MOCK_TICKER))

        with UpbitClient() as client:
            service = client.quotation
            result = service.get_ticker("KRW-BTC")

        ticker = result[0]
        assert isinstance(ticker.timestamp, datetime)
        assert isinstance(ticker.trade_timestamp, datetime)


# --- Async Service Tests ---


class TestAsyncQuotationService:
    """Tests for asynchronous quotation service."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_get_markets(self) -> None:
        """Test async get_markets."""
        respx.get(f"{BASE_URL}/v1/market/all").mock(
            return_value=httpx.Response(200, json=MOCK_MARKETS)
        )

        async with AsyncUpbitClient() as client:
            service = client.quotation
            result = await service.get_markets()

        assert len(result) == 2
        assert result[0]["market"] == "KRW-BTC"

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_get_candles_minutes(self) -> None:
        """Test async get_candles_minutes."""
        respx.get(f"{BASE_URL}/v1/candles/minutes/5").mock(
            return_value=httpx.Response(200, json=MOCK_CANDLE_MINUTE)
        )

        async with AsyncUpbitClient() as client:
            service = client.quotation
            result = await service.get_candles_minutes("KRW-BTC", unit=5)

        assert len(result) == 1
        assert isinstance(result[0], CandleMinute)

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_get_ticker(self) -> None:
        """Test async get_ticker."""
        respx.get(f"{BASE_URL}/v1/ticker").mock(return_value=httpx.Response(200, json=MOCK_TICKER))

        async with AsyncUpbitClient() as client:
            service = client.quotation
            result = await service.get_ticker("KRW-BTC")

        assert len(result) == 1
        assert isinstance(result[0], Ticker)

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_get_orderbook(self) -> None:
        """Test async get_orderbook."""
        respx.get(f"{BASE_URL}/v1/orderbook").mock(
            return_value=httpx.Response(200, json=MOCK_ORDERBOOK)
        )

        async with AsyncUpbitClient() as client:
            service = client.quotation
            result = await service.get_orderbook(["KRW-BTC"])

        assert len(result) == 1
        assert isinstance(result[0], Orderbook)

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_get_trades(self) -> None:
        """Test async get_trades."""
        respx.get(f"{BASE_URL}/v1/trades/ticks").mock(
            return_value=httpx.Response(200, json=MOCK_TRADES)
        )

        async with AsyncUpbitClient() as client:
            service = client.quotation
            result = await service.get_trades("KRW-BTC", count=50)

        assert len(result) == 2
        assert all(isinstance(t, Trade) for t in result)

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_get_candles_days(self) -> None:
        """Test async get_candles_days."""
        respx.get(f"{BASE_URL}/v1/candles/days").mock(
            return_value=httpx.Response(200, json=MOCK_CANDLE_DAY)
        )

        async with AsyncUpbitClient() as client:
            service = client.quotation
            result = await service.get_candles_days("KRW-BTC", count=10)

        assert len(result) == 1
        assert isinstance(result[0], CandleDay)

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_get_candles_weeks(self) -> None:
        """Test async get_candles_weeks."""
        respx.get(f"{BASE_URL}/v1/candles/weeks").mock(
            return_value=httpx.Response(200, json=MOCK_CANDLE_WEEK)
        )

        async with AsyncUpbitClient() as client:
            service = client.quotation
            result = await service.get_candles_weeks("KRW-BTC")

        assert len(result) == 1
        assert isinstance(result[0], CandleWeek)

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_get_candles_months(self) -> None:
        """Test async get_candles_months."""
        respx.get(f"{BASE_URL}/v1/candles/months").mock(
            return_value=httpx.Response(200, json=MOCK_CANDLE_MONTH)
        )

        async with AsyncUpbitClient() as client:
            service = client.quotation
            result = await service.get_candles_months("KRW-BTC")

        assert len(result) == 1
        assert isinstance(result[0], CandleMonth)


# --- Error Response Tests ---


class TestQuotationServiceErrors:
    """Tests for error responses."""

    @respx.mock
    def test_http_error_400(self) -> None:
        """Test 400 Bad Request raises UpbitAPIError."""
        respx.get(f"{BASE_URL}/v1/market/all").mock(
            return_value=httpx.Response(400, json={"error": "Bad Request"})
        )

        with UpbitClient() as client:
            service = client.quotation
            with pytest.raises(UpbitAPIError) as exc_info:
                service.get_markets()
            assert exc_info.value.status_code == 400

    @respx.mock
    def test_http_error_401(self) -> None:
        """Test 401 Unauthorized raises UpbitAuthError."""
        respx.get(f"{BASE_URL}/v1/ticker").mock(
            return_value=httpx.Response(401, json={"error": "Unauthorized"})
        )

        with UpbitClient() as client:
            service = client.quotation
            with pytest.raises(UpbitAuthError):
                service.get_ticker("KRW-BTC")

    @respx.mock
    def test_http_error_429(self) -> None:
        """Test 429 Too Many Requests raises UpbitRateLimitError."""
        respx.get(f"{BASE_URL}/v1/orderbook").mock(
            return_value=httpx.Response(429, json={"error": "Too Many Requests"})
        )

        with UpbitClient() as client:
            service = client.quotation
            with pytest.raises(UpbitRateLimitError):
                service.get_orderbook("KRW-BTC")

    @respx.mock
    def test_http_error_500(self) -> None:
        """Test 500 Internal Server Error raises UpbitAPIError."""
        respx.get(f"{BASE_URL}/v1/trades/ticks").mock(
            return_value=httpx.Response(500, json={"error": "Internal Server Error"})
        )

        with UpbitClient() as client:
            service = client.quotation
            with pytest.raises(UpbitAPIError) as exc_info:
                service.get_trades("KRW-BTC")
            assert exc_info.value.status_code == 500

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_http_error(self) -> None:
        """Test async service raises UpbitAuthError on 403 response."""
        respx.get(f"{BASE_URL}/v1/market/all").mock(
            return_value=httpx.Response(403, json={"error": "Forbidden"})
        )

        async with AsyncUpbitClient() as client:
            service = client.quotation
            with pytest.raises(UpbitAuthError):
                await service.get_markets()
