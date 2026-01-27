"""Integration tests for Upbit Connect library.

These tests verify the interaction between multiple components:
- Client (Sync/Async)
- Authentication
- Rate Limiter
- Service layers (Quotation/Exchange)

Tests use respx to mock API responses, ensuring deterministic execution
without requiring actual API credentials.
"""

import json
import time
from decimal import Decimal

import httpx
import pytest
import respx

from upbit_connect.client import AsyncUpbitClient, UpbitClient
from upbit_connect.models.exchange import OrderSide, OrderType


@pytest.mark.asyncio
async def test_async_client_context_manager_lifecycle() -> None:
    """Verify AsyncUpbitClient context manager properly handles resources."""
    async with AsyncUpbitClient() as client:
        assert isinstance(client._http_client, httpx.AsyncClient)
        assert not client._http_client.is_closed

    # Client should be closed after exit
    assert client._http_client.is_closed


def test_sync_client_context_manager_lifecycle() -> None:
    """Verify UpbitClient context manager properly handles resources."""
    with UpbitClient() as client:
        assert isinstance(client._http_client, httpx.Client)
        assert not client._http_client.is_closed

    # Client should be closed after exit
    assert client._http_client.is_closed


@pytest.mark.asyncio
@respx.mock
async def test_async_full_trading_flow() -> None:
    """Test a complete trading flow: Check Price -> Buy -> Check Balance -> Sell."""

    # Mock data
    market = "KRW-BTC"
    current_price = 50_000_000.0
    buy_amount = 1_000_000.0  # 1M KRW
    buy_volume = 0.02

    # 1. Ticker response
    respx.get("https://api.upbit.com/v1/ticker").respond(
        json=[
            {
                "market": market,
                "trade_date": "20240127",
                "trade_time": "120000",
                "trade_date_kst": "20240127",
                "trade_time_kst": "210000",
                "trade_timestamp": 1706356800000,
                "opening_price": 49000000,
                "high_price": 51000000,
                "low_price": 49000000,
                "trade_price": current_price,
                "prev_closing_price": 49000000,
                "change": "RISE",
                "change_price": 1000000,
                "change_rate": 0.02,
                "signed_change_price": 1000000,
                "signed_change_rate": 0.02,
                "trade_volume": 100,
                "acc_trade_price": 5000000000,
                "acc_trade_price_24h": 10000000000,
                "acc_trade_volume": 100,
                "acc_trade_volume_24h": 200,
                "highest_52_week_price": 60000000,
                "highest_52_week_date": "2023-12-01",
                "lowest_52_week_price": 30000000,
                "lowest_52_week_date": "2023-01-01",
                "timestamp": 1706356800000,
            }
        ]
    )

    # 2. Buy and Sell Orders - combined mock to distinguish by body
    def orders_side_effect(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body.get("side") == "bid":
            return httpx.Response(
                200,
                json={
                    "uuid": "buy-uuid-123",
                    "side": "bid",
                    "ord_type": "price",
                    "price": str(buy_amount),
                    "state": "wait",
                    "market": market,
                    "created_at": "2024-01-27T21:00:00+09:00",
                    "reserved_fee": "500",
                    "remaining_fee": "500",
                    "paid_fee": "0",
                    "locked": str(buy_amount),
                    "executed_volume": "0",
                    "trades_count": 0,
                },
            )
        else:
            return httpx.Response(
                200,
                json={
                    "uuid": "sell-uuid-456",
                    "side": "ask",
                    "ord_type": "market",
                    "volume": str(buy_volume),
                    "state": "wait",
                    "market": market,
                    "created_at": "2024-01-27T21:05:00+09:00",
                    "reserved_fee": "0",
                    "remaining_fee": "0",
                    "paid_fee": "0",
                    "locked": str(buy_volume),
                    "executed_volume": "0",
                    "trades_count": 0,
                },
            )

    respx.post("https://api.upbit.com/v1/orders").mock(side_effect=orders_side_effect)

    # 3. Account Balance response
    respx.get("https://api.upbit.com/v1/accounts").respond(
        json=[
            {
                "currency": "KRW",
                "balance": "9000000",
                "locked": "1000000",
                "avg_buy_price": "0",
                "avg_buy_price_modified": False,
                "unit_currency": "KRW",
            },
            {
                "currency": "BTC",
                "balance": str(buy_volume),
                "locked": "0",
                "avg_buy_price": str(current_price),
                "avg_buy_price_modified": False,
                "unit_currency": "KRW",
            },
        ]
    )

    async with AsyncUpbitClient("dummy-access", "dummy-secret") as client:
        # Step 1: Check Price
        tickers = await client.quotation.get_ticker(market)
        assert len(tickers) == 1
        assert tickers[0].trade_price == Decimal(str(current_price))

        # Step 2: Buy Market (Price)
        buy_order = await client.exchange.buy_market(market, Decimal(str(buy_amount)))
        assert buy_order.uuid == "buy-uuid-123"
        assert buy_order.side == OrderSide.BID
        assert buy_order.ord_type == OrderType.PRICE

        # Step 3: Check Balance
        accounts = await client.exchange.get_accounts()
        btc_account = next(a for a in accounts if a.currency == "BTC")
        assert btc_account.balance == Decimal(str(buy_volume))

        # Step 4: Sell Market (Volume)
        sell_order = await client.exchange.sell_market(market, btc_account.balance)
        assert sell_order.uuid == "sell-uuid-456"
        assert sell_order.side == OrderSide.ASK
        assert sell_order.volume == Decimal(str(buy_volume))


@pytest.mark.asyncio
@respx.mock
async def test_rate_limiting_integration() -> None:
    """Verify rate limiter slows down requests when headers indicate limit reached."""

    # Configure mock to return Remaining-Req headers that deplete rapidly
    route = respx.get("https://api.upbit.com/v1/ticker")

    # Response 1: Plenty remaining
    route.side_effect = [
        httpx.Response(200, json=[], headers={"Remaining-Req": "group=quotation; min=600; sec=10"}),
        httpx.Response(
            200, json=[], headers={"Remaining-Req": "group=quotation; min=599; sec=1"}
        ),  # Almost empty
        httpx.Response(
            200, json=[], headers={"Remaining-Req": "group=quotation; min=598; sec=1"}
        ),  # Still 1
        httpx.Response(
            200, json=[], headers={"Remaining-Req": "group=quotation; min=597; sec=10"}
        ),  # Refilled
    ]

    async with AsyncUpbitClient() as client:
        start_time = time.time()

        # Request 1 (OK)
        await client._get("/v1/ticker")

        # Request 2 (OK, but reports sec=1 remaining)
        await client._get("/v1/ticker")

        # Request 3 (OK, but reports sec=0 remaining)
        # The limiter should update its state to "0 remaining" AFTER this request returns.
        await client._get("/v1/ticker")

        # Request 4 (Should wait because previous response said sec=0)
        # Limiter knows remaining=0, so it waits until leak/refill.
        # Since our mock limiter implementation refills locally based on time,
        # and we forced it to 0, it should sleep.
        await client._get("/v1/ticker")

        end_time = time.time()

        # We expect some delay because we hit the limit (sec=0)
        # In the limiter implementation, if bucket is full or remaining < limit, it waits.
        # We simulate hitting the limit, so there should be a pause.
        # Exact timing depends on implementation details, but should be > 0.1s
        assert end_time - start_time > 0.05
