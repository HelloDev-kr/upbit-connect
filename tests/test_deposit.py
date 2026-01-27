"""Tests for deposit service endpoints.

This module tests DepositService and AsyncDepositService using respx
to mock HTTP responses from the Upbit API.
"""

from decimal import Decimal

import httpx
import pytest
import respx

from upbit_connect.client import AsyncUpbitClient, UpbitClient
from upbit_connect.models.deposit import Deposit, DepositAddress

BASE_URL = "https://api.upbit.com"

MOCK_DEPOSIT = {
    "type": "deposit",
    "uuid": "94332e99-3a87-4a35-9f98-28c30dec18c6",
    "currency": "BTC",
    "net_type": "BTC",
    "txid": "9806e0539ef69427014cf0560299740f915843b13dd2489fe742792c3005f5fe",
    "state": "done",
    "created_at": "2024-01-27T12:00:00+09:00",
    "done_at": "2024-01-27T12:10:00+09:00",
    "amount": "0.01",
    "fee": "0.0",
    "transaction_type": "default",
}

MOCK_DEPOSITS_LIST = [MOCK_DEPOSIT]

MOCK_DEPOSIT_ADDRESS = {
    "currency": "BTC",
    "net_type": "BTC",
    "deposit_address": "3E179H6K7N7G7G7G7G7G7G7G7G7G7G7G",
    "secondary_address": None,
}


class TestDepositService:
    """Tests for synchronous deposit service."""

    @respx.mock
    def test_get_deposits(self) -> None:
        """Test get_deposits returns list of Deposit models."""
        respx.get(f"{BASE_URL}/v1/deposits").mock(
            return_value=httpx.Response(200, json=MOCK_DEPOSITS_LIST)
        )

        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.deposit
            result = service.get_deposits(currency="BTC")

        assert len(result) == 1
        assert isinstance(result[0], Deposit)
        assert result[0].currency == "BTC"
        assert result[0].amount == Decimal("0.01")

    @respx.mock
    def test_get_deposit(self) -> None:
        """Test get_deposit returns a single Deposit model."""
        respx.get(f"{BASE_URL}/v1/deposit").mock(
            return_value=httpx.Response(200, json=MOCK_DEPOSIT)
        )

        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.deposit
            result = service.get_deposit(uuid="94332e99-3a87-4a35-9f98-28c30dec18c6")

        assert isinstance(result, Deposit)
        assert result.uuid == "94332e99-3a87-4a35-9f98-28c30dec18c6"

    @respx.mock
    def test_generate_deposit_address(self) -> None:
        """Test generate_deposit_address returns DepositAddress model."""
        respx.post(f"{BASE_URL}/v1/deposits/generate_coin_address").mock(
            return_value=httpx.Response(200, json=MOCK_DEPOSIT_ADDRESS)
        )

        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.deposit
            result = service.generate_deposit_address(currency="BTC")

        assert isinstance(result, DepositAddress)
        assert result.currency == "BTC"
        assert result.deposit_address == "3E179H6K7N7G7G7G7G7G7G7G7G7G7G7G"

    @respx.mock
    def test_get_deposit_addresses(self) -> None:
        """Test get_deposit_addresses returns list of DepositAddress models."""
        respx.get(f"{BASE_URL}/v1/deposits/coin_addresses").mock(
            return_value=httpx.Response(200, json=[MOCK_DEPOSIT_ADDRESS])
        )

        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.deposit
            result = service.get_deposit_addresses()

        assert len(result) == 1
        assert isinstance(result[0], DepositAddress)

    @respx.mock
    def test_get_deposit_address(self) -> None:
        """Test get_deposit_address returns DepositAddress model."""
        respx.get(f"{BASE_URL}/v1/deposits/coin_address").mock(
            return_value=httpx.Response(200, json=MOCK_DEPOSIT_ADDRESS)
        )

        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.deposit
            result = service.get_deposit_address(currency="BTC")

        assert isinstance(result, DepositAddress)
        assert result.currency == "BTC"

    @respx.mock
    def test_deposit_krw(self) -> None:
        """Test deposit_krw returns Deposit model."""
        mock_krw_deposit = {
            **MOCK_DEPOSIT,
            "currency": "KRW",
            "amount": "100000",
        }
        respx.post(f"{BASE_URL}/v1/deposits/krw").mock(
            return_value=httpx.Response(200, json=mock_krw_deposit)
        )

        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.deposit
            result = service.deposit_krw(amount=Decimal("100000"))

        assert isinstance(result, Deposit)
        assert result.currency == "KRW"
        assert result.amount == Decimal("100000")


class TestAsyncDepositService:
    """Tests for asynchronous deposit service."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_get_deposits(self) -> None:
        """Test async get_deposits."""
        respx.get(f"{BASE_URL}/v1/deposits").mock(
            return_value=httpx.Response(200, json=MOCK_DEPOSITS_LIST)
        )

        async with AsyncUpbitClient(access_key="access", secret_key="secret") as client:
            service = client.deposit
            result = await service.get_deposits(currency="BTC")

        assert len(result) == 1
        assert isinstance(result[0], Deposit)

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_deposit_krw(self) -> None:
        """Test async deposit_krw."""
        mock_krw_deposit = {
            **MOCK_DEPOSIT,
            "currency": "KRW",
            "amount": "100000",
        }
        respx.post(f"{BASE_URL}/v1/deposits/krw").mock(
            return_value=httpx.Response(200, json=mock_krw_deposit)
        )

        async with AsyncUpbitClient(access_key="access", secret_key="secret") as client:
            service = client.deposit
            result = await service.deposit_krw(amount=Decimal("100000"))

        assert isinstance(result, Deposit)
        assert result.currency == "KRW"
