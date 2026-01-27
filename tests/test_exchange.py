"""Tests for exchange service endpoints.

This module tests ExchangeService and AsyncExchangeService using respx
to mock HTTP responses from the Upbit API. Tests cover order placement,
account queries, and price tick validation.
"""

from decimal import Decimal

import httpx
import pytest
import respx

from upbit_connect.client import AsyncUpbitClient, UpbitClient
from upbit_connect.exceptions import (
    UpbitAPIError,
    UpbitAuthError,
    UpbitRateLimitError,
    UpbitValidationError,
)
from upbit_connect.models.exchange import (
    APIKey,
    Asset,
    Order,
    OrderSide,
    OrderType,
    validate_price_tick,
)

BASE_URL = "https://api.upbit.com"


MOCK_ACCOUNTS = [
    {
        "currency": "KRW",
        "balance": "1000000.0",
        "locked": "50000.0",
        "avg_buy_price": "0",
        "avg_buy_price_modified": False,
        "unit_currency": "KRW",
    },
    {
        "currency": "BTC",
        "balance": "0.5",
        "locked": "0.1",
        "avg_buy_price": "50000000",
        "avg_buy_price_modified": True,
        "unit_currency": "KRW",
    },
]

MOCK_ORDER_LIMIT = {
    "uuid": "cdd92199-2897-4e14-9b2c-8db74d5c3d04",
    "side": "bid",
    "ord_type": "limit",
    "price": "50000000",
    "state": "wait",
    "market": "KRW-BTC",
    "created_at": "2024-01-27T12:00:00",
    "volume": "0.001",
    "remaining_volume": "0.001",
    "reserved_fee": "25",
    "remaining_fee": "25",
    "paid_fee": "0",
    "locked": "50025",
    "executed_volume": "0",
    "trades_count": 0,
}

MOCK_ORDER_MARKET_BUY = {
    "uuid": "aaa92199-2897-4e14-9b2c-8db74d5c3d04",
    "side": "bid",
    "ord_type": "price",
    "price": "100000",
    "state": "done",
    "market": "KRW-BTC",
    "created_at": "2024-01-27T12:00:00",
    "volume": None,
    "remaining_volume": None,
    "reserved_fee": "50",
    "remaining_fee": "0",
    "paid_fee": "50",
    "locked": "0",
    "executed_volume": "0.002",
    "trades_count": 1,
}

MOCK_ORDER_MARKET_SELL = {
    "uuid": "bbb92199-2897-4e14-9b2c-8db74d5c3d04",
    "side": "ask",
    "ord_type": "market",
    "price": None,
    "state": "done",
    "market": "KRW-BTC",
    "created_at": "2024-01-27T12:00:00",
    "volume": "0.001",
    "remaining_volume": "0",
    "reserved_fee": "25",
    "remaining_fee": "0",
    "paid_fee": "25",
    "locked": "0",
    "executed_volume": "0.001",
    "trades_count": 1,
}

MOCK_ORDER_CANCELLED = {
    "uuid": "ccc92199-2897-4e14-9b2c-8db74d5c3d04",
    "side": "bid",
    "ord_type": "limit",
    "price": "49000000",
    "state": "cancel",
    "market": "KRW-BTC",
    "created_at": "2024-01-27T11:00:00",
    "volume": "0.002",
    "remaining_volume": "0.002",
    "reserved_fee": "49",
    "remaining_fee": "49",
    "paid_fee": "0",
    "locked": "0",
    "executed_volume": "0",
    "trades_count": 0,
}

MOCK_ORDERS_LIST = [
    MOCK_ORDER_LIMIT,
    {
        **MOCK_ORDER_LIMIT,
        "uuid": "ddd92199-2897-4e14-9b2c-8db74d5c3d04",
        "price": "49500000",
    },
]

MOCK_API_KEYS = [
    {
        "access_key": "access_key_1",
        "expire_at": "2024-12-31T00:00:00Z",
        "permissions": ["asset:read", "order:read"],
    },
    {
        "access_key": "access_key_2",
        "expire_at": "2025-06-30T00:00:00Z",
        "permissions": ["asset:read", "order:read", "order:write"],
    },
]


class TestExchangeService:
    """Tests for synchronous exchange service."""

    @respx.mock
    def test_get_accounts(self) -> None:
        """Test get_accounts returns list of Asset models."""
        respx.get(f"{BASE_URL}/v1/accounts").mock(
            return_value=httpx.Response(200, json=MOCK_ACCOUNTS)
        )

        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            result = service.get_accounts()

        assert len(result) == 2
        assert all(isinstance(a, Asset) for a in result)
        assert result[0].currency == "KRW"
        assert result[0].balance == Decimal("1000000.0")
        assert result[1].currency == "BTC"
        assert result[1].locked == Decimal("0.1")

    @respx.mock
    def test_get_api_keys(self) -> None:
        """Test get_api_keys returns list of APIKey models."""
        respx.get(f"{BASE_URL}/v1/api_keys").mock(
            return_value=httpx.Response(200, json=MOCK_API_KEYS)
        )

        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            result = service.get_api_keys()

        assert len(result) == 2
        assert all(isinstance(k, APIKey) for k in result)
        assert result[0].access_key == "access_key_1"
        assert result[1].permissions == ["asset:read", "order:read", "order:write"]

    @respx.mock
    def test_place_order_limit(self) -> None:
        """Test place_order with LIMIT order type."""
        respx.post(f"{BASE_URL}/v1/orders").mock(
            return_value=httpx.Response(200, json=MOCK_ORDER_LIMIT)
        )

        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            result = service.place_order(
                market="KRW-BTC",
                side=OrderSide.BID,
                ord_type=OrderType.LIMIT,
                price=Decimal("50000000"),
                volume=Decimal("0.001"),
            )

        assert isinstance(result, Order)
        assert result.uuid == "cdd92199-2897-4e14-9b2c-8db74d5c3d04"
        assert result.side == OrderSide.BID
        assert result.ord_type == OrderType.LIMIT
        assert result.price == Decimal("50000000")
        assert result.volume == Decimal("0.001")
        assert result.state == "wait"

    @respx.mock
    def test_place_order_market_buy(self) -> None:
        """Test place_order with PRICE (market buy) order type."""
        respx.post(f"{BASE_URL}/v1/orders").mock(
            return_value=httpx.Response(200, json=MOCK_ORDER_MARKET_BUY)
        )

        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            result = service.place_order(
                market="KRW-BTC",
                side=OrderSide.BID,
                ord_type=OrderType.PRICE,
                price=Decimal("100000"),
            )

        assert isinstance(result, Order)
        assert result.ord_type == OrderType.PRICE
        assert result.price == Decimal("100000")
        assert result.volume is None
        assert result.state == "done"

    @respx.mock
    def test_place_order_market_sell(self) -> None:
        """Test place_order with MARKET (market sell) order type."""
        respx.post(f"{BASE_URL}/v1/orders").mock(
            return_value=httpx.Response(200, json=MOCK_ORDER_MARKET_SELL)
        )

        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            result = service.place_order(
                market="KRW-BTC",
                side=OrderSide.ASK,
                ord_type=OrderType.MARKET,
                volume=Decimal("0.001"),
            )

        assert isinstance(result, Order)
        assert result.ord_type == OrderType.MARKET
        assert result.price is None
        assert result.volume == Decimal("0.001")

    @respx.mock
    def test_buy_limit(self) -> None:
        """Test buy_limit helper method."""
        respx.post(f"{BASE_URL}/v1/orders").mock(
            return_value=httpx.Response(200, json=MOCK_ORDER_LIMIT)
        )

        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            result = service.buy_limit(
                market="KRW-BTC",
                price=Decimal("50000000"),
                volume=Decimal("0.001"),
            )

        assert isinstance(result, Order)
        assert result.side == OrderSide.BID
        assert result.ord_type == OrderType.LIMIT

    @respx.mock
    def test_sell_limit(self) -> None:
        """Test sell_limit helper method."""
        mock_sell = {**MOCK_ORDER_LIMIT, "side": "ask"}
        respx.post(f"{BASE_URL}/v1/orders").mock(return_value=httpx.Response(200, json=mock_sell))

        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            result = service.sell_limit(
                market="KRW-BTC",
                price=Decimal("50000000"),
                volume=Decimal("0.001"),
            )

        assert isinstance(result, Order)
        assert result.side == OrderSide.ASK

    @respx.mock
    def test_buy_market(self) -> None:
        """Test buy_market helper method."""
        respx.post(f"{BASE_URL}/v1/orders").mock(
            return_value=httpx.Response(200, json=MOCK_ORDER_MARKET_BUY)
        )

        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            result = service.buy_market(
                market="KRW-BTC",
                price=Decimal("100000"),
            )

        assert isinstance(result, Order)
        assert result.ord_type == OrderType.PRICE

    @respx.mock
    def test_sell_market(self) -> None:
        """Test sell_market helper method."""
        respx.post(f"{BASE_URL}/v1/orders").mock(
            return_value=httpx.Response(200, json=MOCK_ORDER_MARKET_SELL)
        )

        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            result = service.sell_market(
                market="KRW-BTC",
                volume=Decimal("0.001"),
            )

        assert isinstance(result, Order)
        assert result.ord_type == OrderType.MARKET

    @respx.mock
    def test_get_order_by_uuid(self) -> None:
        """Test get_order lookup by UUID."""
        respx.get(f"{BASE_URL}/v1/order").mock(
            return_value=httpx.Response(200, json=MOCK_ORDER_LIMIT)
        )

        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            result = service.get_order(uuid="cdd92199-2897-4e14-9b2c-8db74d5c3d04")

        assert isinstance(result, Order)
        assert result.uuid == "cdd92199-2897-4e14-9b2c-8db74d5c3d04"

    @respx.mock
    def test_get_order_by_identifier(self) -> None:
        """Test get_order lookup by identifier."""
        mock_order_with_id = {**MOCK_ORDER_LIMIT}
        respx.get(f"{BASE_URL}/v1/order").mock(
            return_value=httpx.Response(200, json=mock_order_with_id)
        )

        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            result = service.get_order(identifier="my-custom-id-123")

        assert isinstance(result, Order)

    def test_get_order_missing_params(self) -> None:
        """Test get_order raises error when no identifier provided."""
        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            with pytest.raises(UpbitValidationError) as exc_info:
                service.get_order()
            assert "uuid or identifier" in str(exc_info.value)

    @respx.mock
    def test_get_orders_with_filters(self) -> None:
        """Test get_orders with market and state filters."""
        respx.get(f"{BASE_URL}/v1/orders").mock(
            return_value=httpx.Response(200, json=MOCK_ORDERS_LIST)
        )

        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            result = service.get_orders(market="KRW-BTC", state="wait")

        assert len(result) == 2
        assert all(isinstance(o, Order) for o in result)

    @respx.mock
    def test_get_orders_with_states_array(self) -> None:
        """Test get_orders with multiple states filter."""
        respx.get(f"{BASE_URL}/v1/orders").mock(
            return_value=httpx.Response(200, json=MOCK_ORDERS_LIST)
        )

        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            result = service.get_orders(states=["wait", "watch"])

        assert len(result) == 2

    @respx.mock
    def test_cancel_order(self) -> None:
        """Test cancel_order by UUID."""
        respx.delete(f"{BASE_URL}/v1/order").mock(
            return_value=httpx.Response(200, json=MOCK_ORDER_CANCELLED)
        )

        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            result = service.cancel_order(uuid="ccc92199-2897-4e14-9b2c-8db74d5c3d04")

        assert isinstance(result, Order)
        assert result.state == "cancel"

    @respx.mock
    def test_cancel_order_by_identifier(self) -> None:
        """Test cancel_order by identifier."""
        respx.delete(f"{BASE_URL}/v1/order").mock(
            return_value=httpx.Response(200, json=MOCK_ORDER_CANCELLED)
        )

        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            result = service.cancel_order(identifier="my-order-id")

        assert isinstance(result, Order)

    def test_cancel_order_missing_params(self) -> None:
        """Test cancel_order raises error when no identifier provided."""
        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            with pytest.raises(UpbitValidationError) as exc_info:
                service.cancel_order()
            assert "uuid or identifier" in str(exc_info.value)


class TestPriceTickValidation:
    """Tests for price tick validation logic."""

    def test_buy_limit_invalid_tick_price(self) -> None:
        """Test buy_limit raises error for invalid tick price."""
        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            with pytest.raises(UpbitValidationError) as exc_info:
                service.buy_limit(
                    market="KRW-BTC",
                    price=Decimal("50000001"),
                    volume=Decimal("0.001"),
                )
            assert "tick size" in str(exc_info.value)

    def test_sell_limit_invalid_tick_price(self) -> None:
        """Test sell_limit raises error for invalid tick price."""
        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            with pytest.raises(UpbitValidationError) as exc_info:
                service.sell_limit(
                    market="KRW-BTC",
                    price=Decimal("1500001"),
                    volume=Decimal("0.001"),
                )
            assert "tick size" in str(exc_info.value)

    def test_validate_price_tick_krw_high(self) -> None:
        """Test KRW market tick validation for high prices (>= 2M)."""
        assert validate_price_tick("KRW-BTC", Decimal("50000000")) is True
        assert validate_price_tick("KRW-BTC", Decimal("50001000")) is True
        assert validate_price_tick("KRW-BTC", Decimal("50000500")) is False

    def test_validate_price_tick_krw_medium(self) -> None:
        """Test KRW market tick validation for medium prices."""
        assert validate_price_tick("KRW-ETH", Decimal("1500000")) is True
        assert validate_price_tick("KRW-ETH", Decimal("1500500")) is True
        assert validate_price_tick("KRW-ETH", Decimal("1500100")) is False

    def test_validate_price_tick_krw_low(self) -> None:
        """Test KRW market tick validation for low prices."""
        assert validate_price_tick("KRW-XRP", Decimal("500")) is True
        assert validate_price_tick("KRW-XRP", Decimal("505")) is True
        assert validate_price_tick("KRW-XRP", Decimal("500.1")) is False

    def test_validate_price_tick_krw_very_low(self) -> None:
        """Test KRW market tick validation for very low prices (< 100)."""
        assert validate_price_tick("KRW-SHIB", Decimal("0.1")) is True
        assert validate_price_tick("KRW-SHIB", Decimal("0.2")) is True
        assert validate_price_tick("KRW-SHIB", Decimal("0.15")) is False

    def test_validate_price_tick_btc(self) -> None:
        """Test BTC market tick validation (satoshi precision)."""
        assert validate_price_tick("BTC-ETH", Decimal("0.07500000")) is True
        assert validate_price_tick("BTC-ETH", Decimal("0.00000001")) is True
        assert validate_price_tick("BTC-ETH", Decimal("0.000000001")) is False

    def test_validate_price_tick_usdt(self) -> None:
        """Test USDT market tick validation."""
        assert validate_price_tick("USDT-BTC", Decimal("50000")) is True
        assert validate_price_tick("USDT-ETH", Decimal("100.1")) is True
        assert validate_price_tick("USDT-XRP", Decimal("0.50001")) is False

    def test_validate_price_tick_unknown_currency(self) -> None:
        """Test unknown quote currency defaults to valid."""
        assert validate_price_tick("EUR-BTC", Decimal("12345.6789")) is True


class TestAsyncExchangeService:
    """Tests for asynchronous exchange service."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_get_accounts(self) -> None:
        """Test async get_accounts."""
        respx.get(f"{BASE_URL}/v1/accounts").mock(
            return_value=httpx.Response(200, json=MOCK_ACCOUNTS)
        )

        async with AsyncUpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            result = await service.get_accounts()

        assert len(result) == 2
        assert all(isinstance(a, Asset) for a in result)

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_get_api_keys(self) -> None:
        """Test async get_api_keys."""
        respx.get(f"{BASE_URL}/v1/api_keys").mock(
            return_value=httpx.Response(200, json=MOCK_API_KEYS)
        )

        async with AsyncUpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            result = await service.get_api_keys()

        assert len(result) == 2
        assert all(isinstance(k, APIKey) for k in result)

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_place_order(self) -> None:
        """Test async place_order."""
        respx.post(f"{BASE_URL}/v1/orders").mock(
            return_value=httpx.Response(200, json=MOCK_ORDER_LIMIT)
        )

        async with AsyncUpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            result = await service.place_order(
                market="KRW-BTC",
                side=OrderSide.BID,
                ord_type=OrderType.LIMIT,
                price=Decimal("50000000"),
                volume=Decimal("0.001"),
            )

        assert isinstance(result, Order)

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_buy_limit(self) -> None:
        """Test async buy_limit."""
        respx.post(f"{BASE_URL}/v1/orders").mock(
            return_value=httpx.Response(200, json=MOCK_ORDER_LIMIT)
        )

        async with AsyncUpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            result = await service.buy_limit(
                market="KRW-BTC",
                price=Decimal("50000000"),
                volume=Decimal("0.001"),
            )

        assert isinstance(result, Order)

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_sell_limit(self) -> None:
        """Test async sell_limit."""
        mock_sell = {**MOCK_ORDER_LIMIT, "side": "ask"}
        respx.post(f"{BASE_URL}/v1/orders").mock(return_value=httpx.Response(200, json=mock_sell))

        async with AsyncUpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            result = await service.sell_limit(
                market="KRW-BTC",
                price=Decimal("50000000"),
                volume=Decimal("0.001"),
            )

        assert isinstance(result, Order)

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_buy_market(self) -> None:
        """Test async buy_market."""
        respx.post(f"{BASE_URL}/v1/orders").mock(
            return_value=httpx.Response(200, json=MOCK_ORDER_MARKET_BUY)
        )

        async with AsyncUpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            result = await service.buy_market("KRW-BTC", Decimal("100000"))

        assert isinstance(result, Order)

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_sell_market(self) -> None:
        """Test async sell_market."""
        respx.post(f"{BASE_URL}/v1/orders").mock(
            return_value=httpx.Response(200, json=MOCK_ORDER_MARKET_SELL)
        )

        async with AsyncUpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            result = await service.sell_market("KRW-BTC", Decimal("0.001"))

        assert isinstance(result, Order)

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_get_order(self) -> None:
        """Test async get_order."""
        respx.get(f"{BASE_URL}/v1/order").mock(
            return_value=httpx.Response(200, json=MOCK_ORDER_LIMIT)
        )

        async with AsyncUpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            result = await service.get_order(uuid="test-uuid")

        assert isinstance(result, Order)

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_get_orders(self) -> None:
        """Test async get_orders."""
        respx.get(f"{BASE_URL}/v1/orders").mock(
            return_value=httpx.Response(200, json=MOCK_ORDERS_LIST)
        )

        async with AsyncUpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            result = await service.get_orders(market="KRW-BTC")

        assert len(result) == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_cancel_order(self) -> None:
        """Test async cancel_order."""
        respx.delete(f"{BASE_URL}/v1/order").mock(
            return_value=httpx.Response(200, json=MOCK_ORDER_CANCELLED)
        )

        async with AsyncUpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            result = await service.cancel_order(uuid="test-uuid")

        assert isinstance(result, Order)
        assert result.state == "cancel"

    @pytest.mark.asyncio
    async def test_async_price_tick_validation_error(self) -> None:
        """Test async buy_limit raises error for invalid tick price."""
        async with AsyncUpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            with pytest.raises(UpbitValidationError):
                await service.buy_limit(
                    market="KRW-BTC",
                    price=Decimal("50000001"),
                    volume=Decimal("0.001"),
                )


class TestExchangeServiceErrors:
    """Tests for error responses."""

    @respx.mock
    def test_http_error_401(self) -> None:
        """Test 401 Unauthorized raises UpbitAuthError."""
        respx.get(f"{BASE_URL}/v1/accounts").mock(
            return_value=httpx.Response(
                401, json={"error": {"name": "invalid_access_key", "message": "Invalid"}}
            )
        )

        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            with pytest.raises(UpbitAuthError):
                service.get_accounts()

    @respx.mock
    def test_http_error_403(self) -> None:
        """Test 403 Forbidden raises UpbitAuthError."""
        respx.post(f"{BASE_URL}/v1/orders").mock(
            return_value=httpx.Response(403, json={"error": "Forbidden"})
        )

        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            with pytest.raises(UpbitAuthError):
                service.place_order(
                    market="KRW-BTC",
                    side=OrderSide.BID,
                    ord_type=OrderType.LIMIT,
                    price=Decimal("50000000"),
                    volume=Decimal("0.001"),
                )

    @respx.mock
    def test_http_error_429(self) -> None:
        """Test 429 Too Many Requests raises UpbitRateLimitError."""
        respx.get(f"{BASE_URL}/v1/orders").mock(
            return_value=httpx.Response(429, json={"error": "Too Many Requests"})
        )

        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            with pytest.raises(UpbitRateLimitError):
                service.get_orders()

    @respx.mock
    def test_http_error_500(self) -> None:
        """Test 500 Internal Server Error raises UpbitAPIError."""
        respx.delete(f"{BASE_URL}/v1/order").mock(
            return_value=httpx.Response(500, json={"error": "Internal Server Error"})
        )

        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            with pytest.raises(UpbitAPIError) as exc_info:
                service.cancel_order(uuid="test-uuid")
            assert exc_info.value.status_code == 500

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_http_error(self) -> None:
        """Test async service raises UpbitAuthError on 401 response."""
        respx.get(f"{BASE_URL}/v1/accounts").mock(
            return_value=httpx.Response(401, json={"error": "Unauthorized"})
        )

        async with AsyncUpbitClient(access_key="access", secret_key="secret") as client:
            service = client.exchange
            with pytest.raises(UpbitAuthError):
                await service.get_accounts()
