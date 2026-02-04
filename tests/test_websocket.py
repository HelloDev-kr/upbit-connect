"""Tests for upbit_connect.websocket module.

Tests cover WebSocket client functionality including:
- Connection and reconnection
- Subscription management
- Message parsing and dispatching
- Callback invocation
- Private channel authentication
- Error handling
"""

import asyncio
import json
from datetime import datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import websockets.exceptions

from upbit_connect.exceptions import UpbitError
from upbit_connect.models.exchange import Asset, Order
from upbit_connect.models.websocket import (
    AskBid,
    ChangeType,
    MarketState,
    MarketWarning,
    StreamType,
    WsOrderbook,
    WsOrderbookUnit,
    WsTicker,
    WsTrade,
)
from upbit_connect.websocket.client import UpbitWebSocket


class MockConnection:
    def __init__(
        self, messages: list[Any] | None = None, exception: BaseException | None = None
    ) -> None:
        self.messages = messages or []
        self.exception = exception
        self.sent_messages: list[Any] = []
        self.closed = False

    def __aiter__(self) -> Any:
        return self._async_gen()

    async def _async_gen(self) -> Any:
        for msg in self.messages:
            yield msg
        if self.exception:
            raise self.exception

    async def send(self, message: Any) -> None:
        self.sent_messages.append(message)

    async def close(self) -> None:
        self.closed = True


class TestWebSocketInitialization:
    """Tests for UpbitWebSocket initialization."""

    def test_initialization_without_credentials(self) -> None:
        """Test initialization without API credentials."""
        ws = UpbitWebSocket()
        assert ws.access_key is None
        assert ws.secret_key is None
        assert ws.websocket is None
        assert ws.subscriptions == []
        assert ws.running is False
        assert ws._reconnect_delay == ws.RECONNECT_DELAY

    def test_initialization_with_credentials(self) -> None:
        """Test initialization with API credentials."""
        ws = UpbitWebSocket(access_key="test_access", secret_key="test_secret")
        assert ws.access_key == "test_access"
        assert ws.secret_key == "test_secret"
        assert ws.websocket is None
        assert ws.subscriptions == []
        assert ws.running is False

    def test_class_constants(self) -> None:
        """Test class constants are properly defined."""
        assert UpbitWebSocket.WS_URL == "wss://api.upbit.com/websocket/v1"
        assert UpbitWebSocket.PING_INTERVAL == 30.0
        assert UpbitWebSocket.PING_TIMEOUT == 10.0
        assert UpbitWebSocket.RECONNECT_DELAY == 1.0
        assert UpbitWebSocket.MAX_RECONNECT_DELAY == 60.0


class TestWebSocketConnect:
    """Tests for WebSocket connection."""

    @pytest.mark.asyncio
    async def test_connect_success(self) -> None:
        """Test successful WebSocket connection."""
        ws = UpbitWebSocket()
        mock_connection = AsyncMock()

        with patch(
            "upbit_connect.websocket.client.websockets.connect", new_callable=AsyncMock
        ) as mock_connect:
            mock_connect.return_value = mock_connection
            await ws.connect()

            mock_connect.assert_called_once_with(
                ws.WS_URL,
                ping_interval=ws.PING_INTERVAL,
                ping_timeout=ws.PING_TIMEOUT,
            )
            assert ws.websocket is mock_connection
            assert ws.running is True
            assert ws._reconnect_delay == ws.RECONNECT_DELAY

    @pytest.mark.asyncio
    async def test_connect_failure(self) -> None:
        """Test connection failure raises UpbitError."""
        ws = UpbitWebSocket()

        with patch(
            "upbit_connect.websocket.client.websockets.connect", new_callable=AsyncMock
        ) as mock_connect:
            mock_connect.side_effect = Exception("Connection refused")

            with pytest.raises(UpbitError) as exc_info:
                await ws.connect()

            assert "WebSocket connection failed" in str(exc_info.value)
            assert ws.websocket is None
            assert ws.running is False

    @pytest.mark.asyncio
    async def test_connect_resets_reconnect_delay(self) -> None:
        """Test successful connection resets reconnect delay."""
        ws = UpbitWebSocket()
        ws._reconnect_delay = 32.0
        mock_connection = AsyncMock()

        with patch(
            "upbit_connect.websocket.client.websockets.connect", new_callable=AsyncMock
        ) as mock_connect:
            mock_connect.return_value = mock_connection
            await ws.connect()

            assert ws._reconnect_delay == ws.RECONNECT_DELAY


class TestWebSocketSubscribe:
    """Tests for subscription management."""

    @pytest.mark.asyncio
    async def test_subscribe_not_connected(self) -> None:
        """Test subscribe raises UpbitError when not connected."""
        ws = UpbitWebSocket()

        with pytest.raises(UpbitError) as exc_info:
            await ws.subscribe("ticket", [{"type": "ticker", "codes": ["KRW-BTC"]}])

        assert "Not connected to WebSocket" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_subscribe_public_channel(self) -> None:
        """Test subscribing to public channel."""
        ws = UpbitWebSocket()
        mock_connection = AsyncMock()
        ws.websocket = mock_connection
        ws.running = True

        channels = [{"type": "ticker", "codes": ["KRW-BTC", "KRW-ETH"]}]
        await ws.subscribe("my-ticket", channels)

        sent_message = mock_connection.send.call_args[0][0]
        sent_data = json.loads(sent_message)

        assert sent_data[0] == {"ticket": "my-ticket"}
        assert sent_data[1] == {"type": "ticker", "codes": ["KRW-BTC", "KRW-ETH"]}
        assert sent_data[2] == {"format": "DEFAULT"}

        assert ("my-ticket", channels) in ws.subscriptions

    @pytest.mark.asyncio
    async def test_subscribe_with_options(self) -> None:
        """Test subscribing with isOnlyRealtime and isOnlySnapshot options."""
        ws = UpbitWebSocket()
        mock_connection = AsyncMock()
        ws.websocket = mock_connection
        ws.running = True

        channels = [
            {"type": "ticker", "codes": ["KRW-BTC"], "isOnlyRealtime": True},
            {"type": "orderbook", "codes": ["KRW-ETH"], "isOnlySnapshot": True},
        ]
        await ws.subscribe("my-ticket", channels)

        sent_message = mock_connection.send.call_args[0][0]
        sent_data = json.loads(sent_message)

        assert sent_data[1] == {"type": "ticker", "codes": ["KRW-BTC"], "isOnlyRealtime": True}
        assert sent_data[2] == {"type": "orderbook", "codes": ["KRW-ETH"], "isOnlySnapshot": True}

    @pytest.mark.asyncio
    async def test_subscribe_private_channel_with_auth(self) -> None:
        """Test subscribing to private channel includes JWT auth."""
        ws = UpbitWebSocket(access_key="test_access", secret_key="test_secret")
        mock_connection = AsyncMock()
        ws.websocket = mock_connection
        ws.running = True

        channels = [{"type": "myOrder"}]

        with patch("upbit_connect.websocket.client.generate_jwt_token") as mock_jwt:
            mock_jwt.return_value = "mock_jwt_token"
            await ws.subscribe("private-ticket", channels)

            mock_jwt.assert_called_once_with("test_access", "test_secret", None, None)

            sent_message = mock_connection.send.call_args[0][0]
            sent_data = json.loads(sent_message)

            assert sent_data[0] == {"ticket": "private-ticket", "auth": "mock_jwt_token"}
            assert sent_data[1] == {"type": "myOrder"}

    @pytest.mark.asyncio
    async def test_subscribe_private_channel_without_auth(self) -> None:
        """Test private channel without credentials doesn't add auth."""
        ws = UpbitWebSocket()
        mock_connection = AsyncMock()
        ws.websocket = mock_connection
        ws.running = True

        channels = [{"type": "myOrder"}]
        await ws.subscribe("private-ticket", channels)

        sent_message = mock_connection.send.call_args[0][0]
        sent_data = json.loads(sent_message)

        assert sent_data[0] == {"ticket": "private-ticket"}

    @pytest.mark.asyncio
    async def test_subscribe_mixed_public_private(self) -> None:
        """Test subscribing to mixed public and private channels."""
        ws = UpbitWebSocket(access_key="test_access", secret_key="test_secret")
        mock_connection = AsyncMock()
        ws.websocket = mock_connection
        ws.running = True

        channels: list[dict[str, Any]] = [
            {"type": "ticker", "codes": ["KRW-BTC"]},
            {"type": "myAsset"},
        ]

        with patch("upbit_connect.websocket.client.generate_jwt_token") as mock_jwt:
            mock_jwt.return_value = "mock_jwt_token"
            await ws.subscribe("mixed-ticket", channels)

            sent_message = mock_connection.send.call_args[0][0]
            sent_data = json.loads(sent_message)

            assert "auth" in sent_data[0]


class TestWebSocketUnsubscribe:
    """Tests for unsubscription."""

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_from_tracking(self) -> None:
        """Test unsubscribe removes subscription from tracking."""
        ws = UpbitWebSocket()
        ws.subscriptions = [
            ("ticket-1", [{"type": "ticker"}]),
            ("ticket-2", [{"type": "orderbook"}]),
            ("ticket-3", [{"type": "trade"}]),
        ]

        await ws.unsubscribe("ticket-2")

        assert len(ws.subscriptions) == 2
        assert ("ticket-1", [{"type": "ticker"}]) in ws.subscriptions
        assert ("ticket-3", [{"type": "trade"}]) in ws.subscriptions
        assert ("ticket-2", [{"type": "orderbook"}]) not in ws.subscriptions

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_ticket(self) -> None:
        """Test unsubscribe with nonexistent ticket does nothing."""
        ws = UpbitWebSocket()
        ws.subscriptions = [("ticket-1", [{"type": "ticker"}])]

        await ws.unsubscribe("nonexistent")

        assert len(ws.subscriptions) == 1

    @pytest.mark.asyncio
    async def test_unsubscribe_all_matching(self) -> None:
        """Test unsubscribe removes all subscriptions with matching ticket."""
        ws = UpbitWebSocket()
        ws.subscriptions = [
            ("ticket-1", [{"type": "ticker"}]),
            ("ticket-1", [{"type": "orderbook"}]),
        ]

        await ws.unsubscribe("ticket-1")

        assert len(ws.subscriptions) == 0


class TestMessageDispatch:
    """Tests for message type dispatch and parsing."""

    def _create_ticker_data(self) -> dict[str, Any]:
        """Create sample ticker data for WebSocket with proper Pydantic-compatible types."""
        return {
            "type": "ticker",
            "code": "KRW-BTC",
            "opening_price": Decimal("50000000"),
            "high_price": Decimal("51000000"),
            "low_price": Decimal("49000000"),
            "trade_price": Decimal("50500000"),
            "prev_closing_price": Decimal("50000000"),
            "change": ChangeType.RISE,
            "change_price": Decimal("500000"),
            "signed_change_price": Decimal("500000"),
            "change_rate": Decimal("0.01"),
            "signed_change_rate": Decimal("0.01"),
            "ask_bid": AskBid.BID,
            "trade_volume": Decimal("0.001"),
            "acc_trade_volume": Decimal("20"),
            "acc_trade_volume_24h": Decimal("40"),
            "acc_trade_price": Decimal("1000000000"),
            "acc_trade_price_24h": Decimal("2000000000"),
            "acc_ask_volume": Decimal("10"),
            "acc_bid_volume": Decimal("10"),
            "trade_date": "20260127",
            "trade_time": "120000",
            "trade_timestamp": datetime(2026, 1, 27, 12, 0, 0),
            "highest_52_week_price": Decimal("70000000"),
            "highest_52_week_date": "2025-12-01",
            "lowest_52_week_price": Decimal("30000000"),
            "lowest_52_week_date": "2025-06-01",
            "market_state": MarketState.ACTIVE,
            "is_trading_suspended": False,
            "delisting_date": None,
            "market_warning": MarketWarning.NONE,
            "timestamp": datetime(2026, 1, 27, 12, 0, 0),
            "stream_type": StreamType.REALTIME,
        }

    def _create_orderbook_data(self) -> dict[str, Any]:
        """Create sample orderbook data for WebSocket with proper Pydantic-compatible types."""
        return {
            "type": "orderbook",
            "code": "KRW-BTC",
            "timestamp": datetime(2026, 1, 27, 12, 0, 0),
            "total_ask_size": Decimal("10.5"),
            "total_bid_size": Decimal("15.2"),
            "orderbook_units": [
                {
                    "ask_price": Decimal("50100000"),
                    "bid_price": Decimal("50000000"),
                    "ask_size": Decimal("1.5"),
                    "bid_size": Decimal("2.0"),
                }
            ],
            "stream_type": StreamType.REALTIME,
            "level": 0,
        }

    def _create_trade_data(self) -> dict[str, Any]:
        """Create sample trade data for WebSocket with proper Pydantic-compatible types."""
        return {
            "type": "trade",
            "code": "KRW-BTC",
            "timestamp": datetime(2026, 1, 27, 12, 0, 0),
            "trade_date": "2026-01-27",
            "trade_time": "12:00:00",
            "trade_timestamp": datetime(2026, 1, 27, 12, 0, 0),
            "trade_price": Decimal("50500000"),
            "trade_volume": Decimal("0.001"),
            "ask_bid": AskBid.BID,
            "prev_closing_price": Decimal("50000000"),
            "change": ChangeType.RISE,
            "change_price": Decimal("500000"),
            "sequential_id": 1234567890,
            "best_ask_price": Decimal("50600000"),
            "best_ask_size": Decimal("1.5"),
            "best_bid_price": Decimal("50500000"),
            "best_bid_size": Decimal("2.0"),
            "stream_type": StreamType.REALTIME,
        }

    def _create_order_data(self) -> dict[str, Any]:
        """Create sample order data for myOrder channel."""
        return {
            "type": "myOrder",
            "uuid": "test-uuid-12345",
            "side": "bid",
            "ord_type": "limit",
            "price": "50000000",
            "state": "wait",
            "market": "KRW-BTC",
            "created_at": "2026-01-27T12:00:00",
            "volume": "0.001",
            "remaining_volume": "0.001",
            "reserved_fee": "25",
            "remaining_fee": "25",
            "paid_fee": "0",
            "locked": "50025",
            "executed_volume": "0",
            "trades_count": 0,
        }

    def _create_asset_data(self) -> dict[str, Any]:
        """Create sample asset data for myAsset channel."""
        return {
            "type": "myAsset",
            "currency": "KRW",
            "balance": "1000000",
            "locked": "50000",
            "avg_buy_price": "0",
            "avg_buy_price_modified": False,
            "unit_currency": "KRW",
        }

    def test_parse_ticker_message(self) -> None:
        """Test parsing ticker message returns WsTicker model."""
        ws = UpbitWebSocket()
        data = self._create_ticker_data()

        result = ws._parse_message(data)

        assert isinstance(result, WsTicker)
        assert result.code == "KRW-BTC"
        assert result.trade_price == Decimal("50500000")

    def test_parse_orderbook_message(self) -> None:
        """Test parsing orderbook message returns WsOrderbook model."""
        ws = UpbitWebSocket()
        data = self._create_orderbook_data()

        result = ws._parse_message(data)

        assert isinstance(result, WsOrderbook)
        assert result.code == "KRW-BTC"
        assert len(result.orderbook_units) == 1

    def test_parse_trade_message(self) -> None:
        """Test parsing trade message returns WsTrade model."""
        ws = UpbitWebSocket()
        data = self._create_trade_data()

        result = ws._parse_message(data)

        assert isinstance(result, WsTrade)
        assert result.code == "KRW-BTC"
        assert result.trade_volume == Decimal("0.001")

    def test_parse_my_order_message(self) -> None:
        """Test parsing myOrder message returns Order model."""
        ws = UpbitWebSocket()
        data = self._create_order_data()

        result = ws._parse_message(data)

        assert isinstance(result, Order)
        assert result.uuid == "test-uuid-12345"
        assert result.market == "KRW-BTC"

    def test_parse_my_asset_message(self) -> None:
        """Test parsing myAsset message returns Asset model."""
        ws = UpbitWebSocket()
        data = self._create_asset_data()

        result = ws._parse_message(data)

        assert isinstance(result, Asset)
        assert result.currency == "KRW"
        assert result.balance == Decimal("1000000")

    def test_parse_unknown_type(self) -> None:
        """Test parsing unknown message type returns raw dict."""
        ws = UpbitWebSocket()
        data = {"type": "unknown", "foo": "bar"}

        result = ws._parse_message(data)

        assert isinstance(result, dict)
        assert result == data

    def test_parse_no_type_field(self) -> None:
        """Test parsing message without type field returns raw dict."""
        ws = UpbitWebSocket()
        data = {"foo": "bar", "baz": 123}

        result = ws._parse_message(data)

        assert isinstance(result, dict)
        assert result == data


class TestCallbackInvocation:
    """Tests for callback invocation during run loop."""

    @pytest.mark.asyncio
    async def test_callback_invoked_with_raw_message(self) -> None:
        """Test callback is invoked with message from WebSocket."""
        ws = UpbitWebSocket()

        unknown_data = {"type": "unknown", "data": "test"}
        message_bytes = json.dumps(unknown_data).encode("utf-8")

        class InnerMockConnection:
            async def __aiter__(self) -> Any:
                yield message_bytes
                raise websockets.exceptions.ConnectionClosed(None, None)

            async def close(self) -> None:
                pass

        mock_connection = InnerMockConnection()
        ws.websocket = mock_connection  # type: ignore
        ws.running = True

        received_messages: list[Any] = []

        async def callback(msg: Any) -> None:
            received_messages.append(msg)
            ws.running = False

        with patch("upbit_connect.websocket.client.asyncio.sleep", new_callable=AsyncMock):
            await ws.run(callback)

        assert len(received_messages) == 1
        assert received_messages[0] == unknown_data

    @pytest.mark.asyncio
    async def test_callback_invoked_with_text_message(self) -> None:
        """Test callback handles text (non-bytes) messages."""
        ws = UpbitWebSocket()

        unknown_data = {"type": "unknown", "text": "value"}
        message_text = json.dumps(unknown_data)

        mock_connection = MockConnection(
            messages=[message_text], exception=websockets.exceptions.ConnectionClosed(None, None)
        )

        ws.websocket = mock_connection  # type: ignore
        ws.running = True

        received_messages: list[Any] = []

        async def callback(msg: Any) -> None:
            received_messages.append(msg)
            ws.running = False

        with patch("upbit_connect.websocket.client.asyncio.sleep", new_callable=AsyncMock):
            await ws.run(callback)

        assert len(received_messages) == 1
        assert received_messages[0] == unknown_data


class TestAutoReconnect:
    """Tests for auto-reconnect functionality."""

    @pytest.mark.asyncio
    async def test_auto_reconnect_on_connection_closed(self) -> None:
        """Test auto-reconnect triggers on ConnectionClosed."""
        ws = UpbitWebSocket()

        connect_count = 0

        async def mock_connect_func(*args: Any, **kwargs: Any) -> MockConnection:
            nonlocal connect_count
            connect_count += 1
            return MockConnection(exception=websockets.exceptions.ConnectionClosed(None, None))

        async def callback(msg: Any) -> None:
            pass

        call_count = 0

        async def mock_sleep(delay: float) -> None:
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                ws.running = False

        with patch(
            "upbit_connect.websocket.client.websockets.connect", side_effect=mock_connect_func
        ):
            with patch("upbit_connect.websocket.client.asyncio.sleep", side_effect=mock_sleep):
                await ws.connect()
                await ws.run(callback)

        assert connect_count >= 1

    @pytest.mark.asyncio
    async def test_websocket_set_to_none_on_disconnect(self) -> None:
        """Test websocket is set to None on disconnect for reconnect."""
        ws = UpbitWebSocket()
        ws.running = True

        mock_connection = MockConnection(
            exception=websockets.exceptions.ConnectionClosed(None, None)
        )
        ws.websocket = mock_connection  # type: ignore

        async def callback(msg: Any) -> None:
            pass

        async def mock_sleep(delay: float) -> None:
            ws.running = False

        with patch("upbit_connect.websocket.client.websockets.connect", new_callable=AsyncMock):
            with patch("upbit_connect.websocket.client.asyncio.sleep", side_effect=mock_sleep):
                await ws.run(callback)

        assert ws.websocket is None


class TestExponentialBackoff:
    """Tests for exponential backoff on reconnect failures."""

    @pytest.mark.asyncio
    async def test_exponential_backoff_doubles_delay(self) -> None:
        """Test reconnect delay doubles after each failure."""
        ws = UpbitWebSocket()
        ws.running = True
        ws._reconnect_delay = 1.0

        async def callback(msg: Any) -> None:
            pass

        recorded_delays: list[float] = []

        async def mock_sleep(delay: float) -> None:
            recorded_delays.append(delay)
            if len(recorded_delays) >= 3:
                ws.running = False

        with patch(
            "upbit_connect.websocket.client.websockets.connect", new_callable=AsyncMock
        ) as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")
            with patch("upbit_connect.websocket.client.asyncio.sleep", side_effect=mock_sleep):
                await ws.run(callback)

        assert recorded_delays[0] == 1.0
        assert recorded_delays[1] == 2.0
        assert recorded_delays[2] == 4.0

    @pytest.mark.asyncio
    async def test_max_reconnect_delay_capped(self) -> None:
        """Test reconnect delay is capped at MAX_RECONNECT_DELAY."""
        ws = UpbitWebSocket()
        ws.running = True
        ws._reconnect_delay = 32.0

        async def callback(msg: Any) -> None:
            pass

        recorded_delays: list[float] = []

        async def mock_sleep(delay: float) -> None:
            recorded_delays.append(delay)
            if len(recorded_delays) >= 3:
                ws.running = False

        with patch(
            "upbit_connect.websocket.client.websockets.connect", new_callable=AsyncMock
        ) as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")
            with patch("upbit_connect.websocket.client.asyncio.sleep", side_effect=mock_sleep):
                await ws.run(callback)

        assert recorded_delays[0] == 32.0
        assert recorded_delays[1] == 60.0
        assert recorded_delays[2] == 60.0


class TestResubscribeAfterReconnect:
    """Tests for re-subscription after reconnect."""

    @pytest.mark.asyncio
    async def test_resubscribe_restores_all_subscriptions(self) -> None:
        """Test _resubscribe restores all tracked subscriptions."""
        ws = UpbitWebSocket()
        mock_connection = MockConnection()
        ws.websocket = mock_connection  # type: ignore
        ws.running = True

        ws.subscriptions = [
            ("ticket-1", [{"type": "ticker", "codes": ["KRW-BTC"]}]),
            ("ticket-2", [{"type": "orderbook", "codes": ["KRW-ETH"]}]),
        ]

        await ws._resubscribe()

        assert len(mock_connection.sent_messages) == 2
        assert len(ws.subscriptions) == 2

    @pytest.mark.asyncio
    async def test_resubscribe_clears_and_restores(self) -> None:
        """Test _resubscribe clears subscriptions before restoring."""
        ws = UpbitWebSocket()
        mock_connection = MockConnection()
        ws.websocket = mock_connection  # type: ignore
        ws.running = True

        original_subs = [
            ("ticket-1", [{"type": "ticker", "codes": ["KRW-BTC"]}]),
        ]
        ws.subscriptions = list(original_subs)

        await ws._resubscribe()

        assert ws.subscriptions == original_subs

    @pytest.mark.asyncio
    async def test_run_calls_resubscribe_after_reconnect(self) -> None:
        """Test run() calls _resubscribe after reconnection."""
        ws = UpbitWebSocket()

        resubscribe_called = False

        async def mock_resubscribe() -> None:
            nonlocal resubscribe_called
            resubscribe_called = True

        connect_count = 0

        async def mock_connect() -> None:
            nonlocal connect_count
            connect_count += 1
            ws.websocket = MockConnection(  # type: ignore[assignment]
                exception=websockets.exceptions.ConnectionClosed(None, None)
            )
            ws.running = True

        ws.connect = mock_connect  # type: ignore[method-assign]
        ws._resubscribe = mock_resubscribe  # type: ignore[method-assign]
        ws.subscriptions = [("ticket", [{"type": "ticker"}])]

        async def mock_sleep(delay: float) -> None:
            ws.running = False

        async def callback(msg: Any) -> None:
            pass

        with patch("upbit_connect.websocket.client.asyncio.sleep", side_effect=mock_sleep):
            ws.running = True
            ws.websocket = None
            await ws.run(callback)

        assert resubscribe_called


class TestClose:
    """Tests for graceful shutdown."""

    @pytest.mark.asyncio
    async def test_close_sets_running_false(self) -> None:
        """Test close sets running to False."""
        ws = UpbitWebSocket()
        ws.running = True

        await ws.close()

        assert ws.running is False

    @pytest.mark.asyncio
    async def test_close_closes_websocket(self) -> None:
        """Test close calls websocket.close()."""
        ws = UpbitWebSocket()
        mock_connection = MockConnection()
        ws.websocket = mock_connection  # type: ignore
        ws.running = True

        await ws.close()

        assert mock_connection.closed is True
        assert ws.websocket is None

    @pytest.mark.asyncio
    async def test_close_without_connection(self) -> None:
        """Test close without active connection does not error."""
        ws = UpbitWebSocket()
        ws.running = True
        ws.websocket = None

        await ws.close()

        assert ws.running is False


class TestMalformedMessageHandling:
    """Tests for malformed message handling."""

    @pytest.mark.asyncio
    async def test_malformed_json_handling(self) -> None:
        """Test malformed JSON in message causes exception handling."""
        ws = UpbitWebSocket()
        ws.running = True

        mock_connection = MockConnection(messages=[b"not valid json{"])
        ws.websocket = mock_connection  # type: ignore

        async def callback(msg: Any) -> None:
            pass

        async def mock_sleep(delay: float) -> None:
            ws.running = False

        with patch("upbit_connect.websocket.client.websockets.connect", new_callable=AsyncMock):
            with patch("upbit_connect.websocket.client.asyncio.sleep", side_effect=mock_sleep):
                await ws.run(callback)

        assert ws.websocket is None


class TestCancelledError:
    """Tests for asyncio.CancelledError handling."""

    @pytest.mark.asyncio
    async def test_cancelled_error_stops_running(self) -> None:
        """Test CancelledError sets running to False and re-raises."""
        ws = UpbitWebSocket()
        ws.running = True

        mock_connection = MockConnection(exception=asyncio.CancelledError())
        ws.websocket = mock_connection  # type: ignore

        async def callback(msg: Any) -> None:
            pass

        with pytest.raises(asyncio.CancelledError):
            await ws.run(callback)

        assert ws.running is False


class TestPrivateChannelAuthentication:
    """Tests for private channel JWT authentication."""

    @pytest.mark.asyncio
    async def test_myorder_requires_auth(self) -> None:
        """Test myOrder channel triggers JWT generation."""
        ws = UpbitWebSocket(access_key="ak", secret_key="sk")
        mock_connection = AsyncMock()
        ws.websocket = mock_connection
        ws.running = True

        with patch("upbit_connect.websocket.client.generate_jwt_token") as mock_jwt:
            mock_jwt.return_value = "jwt_token"

            await ws.subscribe("t", [{"type": "myOrder"}])

            mock_jwt.assert_called_once_with("ak", "sk", None, None)

    @pytest.mark.asyncio
    async def test_myasset_requires_auth(self) -> None:
        """Test myAsset channel triggers JWT generation."""
        ws = UpbitWebSocket(access_key="ak", secret_key="sk")
        mock_connection = AsyncMock()
        ws.websocket = mock_connection
        ws.running = True

        with patch("upbit_connect.websocket.client.generate_jwt_token") as mock_jwt:
            mock_jwt.return_value = "jwt_token"

            await ws.subscribe("t", [{"type": "myAsset"}])

            mock_jwt.assert_called_once_with("ak", "sk", None, None)

    @pytest.mark.asyncio
    async def test_public_channels_no_auth(self) -> None:
        """Test public channels do not trigger JWT generation."""
        ws = UpbitWebSocket(access_key="ak", secret_key="sk")
        mock_connection = AsyncMock()
        ws.websocket = mock_connection
        ws.running = True

        with patch("upbit_connect.websocket.client.generate_jwt_token") as mock_jwt:
            await ws.subscribe(
                "t",
                [
                    {"type": "ticker", "codes": ["KRW-BTC"]},
                    {"type": "orderbook", "codes": ["KRW-BTC"]},
                    {"type": "trade", "codes": ["KRW-BTC"]},
                ],
            )

            mock_jwt.assert_not_called()
