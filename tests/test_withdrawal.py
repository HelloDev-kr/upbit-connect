"""Tests for withdrawal service endpoints.

This module tests WithdrawalService and AsyncWithdrawalService using respx
to mock HTTP responses from the Upbit API.
"""

from decimal import Decimal

import httpx
import pytest
import respx

from upbit_connect.client import AsyncUpbitClient, UpbitClient
from upbit_connect.models.withdrawal import Withdrawal, WithdrawalChance

BASE_URL = "https://api.upbit.com"

MOCK_WITHDRAWAL = {
    "type": "withdraw",
    "uuid": "35a1f03-60cc-40cc-8714-469b6574f260",
    "currency": "BTC",
    "net_type": "BTC",
    "txid": "9806e0539ef69427014cf0560299740f915843b13dd2489fe742792c3005f5fe",
    "state": "done",
    "created_at": "2024-01-27T12:00:00+09:00",
    "done_at": "2024-01-27T12:10:00+09:00",
    "amount": "0.01",
    "fee": "0.0005",
    "transaction_type": "default",
    "is_cancelable": False,
}

MOCK_WITHDRAWALS_LIST = [MOCK_WITHDRAWAL]

MOCK_WITHDRAWAL_CHANCE = {
    "member_level": {
        "security_level": 4,
        "fee_level": 0,
        "email_verified": True,
        "identity_verified": True,
        "bank_account_verified": True,
        "kakao_pay_auth_verified": True,
        "second_auth_verified": True,
        "deposit_user_level": 4,
    },
    "currency": {
        "code": "BTC",
        "withdraw_fee": "0.0009",
        "is_coin": True,
        "wallet_state": "working",
        "wallet_support": ["deposit", "withdraw"],
    },
    "account": {
        "currency": "BTC",
        "balance": "10.0",
        "locked": "0.0",
        "avg_buy_price": "50000000",
        "avg_buy_price_modified": False,
        "unit_currency": "KRW",
    },
    "withdrawal_limit": {
        "currency": "BTC",
        "minimum": "0.001",
        "fixed": 8,
        "can_withdraw": True,
        "maximum": "100.0",
        "onetime": "50.0",
        "daily": "100.0",
        "remain_onetime": "50.0",
        "remain_daily": "100.0",
    },
}


class TestWithdrawalService:
    """Tests for synchronous withdrawal service."""

    @respx.mock
    def test_get_withdrawals(self) -> None:
        """Test get_withdrawals returns list of Withdrawal models."""
        respx.get(f"{BASE_URL}/v1/withdraws").mock(
            return_value=httpx.Response(200, json=MOCK_WITHDRAWALS_LIST)
        )

        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.withdrawal
            result = service.get_withdrawals(currency="BTC")

        assert len(result) == 1
        assert isinstance(result[0], Withdrawal)
        assert result[0].currency == "BTC"
        assert result[0].amount == Decimal("0.01")

    @respx.mock
    def test_get_withdrawal(self) -> None:
        """Test get_withdrawal returns a single Withdrawal model."""
        respx.get(f"{BASE_URL}/v1/withdraw").mock(
            return_value=httpx.Response(200, json=MOCK_WITHDRAWAL)
        )

        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.withdrawal
            result = service.get_withdrawal(uuid="35a1f03-60cc-40cc-8714-469b6574f260")

        assert isinstance(result, Withdrawal)
        assert result.uuid == "35a1f03-60cc-40cc-8714-469b6574f260"

    @respx.mock
    def test_get_withdrawal_chance(self) -> None:
        """Test get_withdrawal_chance returns WithdrawalChance model."""
        respx.get(f"{BASE_URL}/v1/withdraws/chance").mock(
            return_value=httpx.Response(200, json=MOCK_WITHDRAWAL_CHANCE)
        )

        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.withdrawal
            result = service.get_withdrawal_chance(currency="BTC")

        assert isinstance(result, WithdrawalChance)
        assert result.currency.code == "BTC"
        assert result.withdrawal_limit.can_withdraw is True
        assert result.account.balance == Decimal("10.0")

    @respx.mock
    def test_withdraw_coin(self) -> None:
        """Test withdraw (coin) returns Withdrawal model."""
        respx.post(f"{BASE_URL}/v1/withdraws/coin").mock(
            return_value=httpx.Response(200, json=MOCK_WITHDRAWAL)
        )

        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.withdrawal
            result = service.withdraw(
                currency="BTC",
                amount=Decimal("0.01"),
                address="test-address",
            )

        assert isinstance(result, Withdrawal)
        assert result.currency == "BTC"
        assert result.amount == Decimal("0.01")

    @respx.mock
    def test_withdraw_krw(self) -> None:
        """Test withdraw_krw returns Withdrawal model."""
        mock_krw_withdrawal = {
            **MOCK_WITHDRAWAL,
            "currency": "KRW",
            "amount": "100000",
            "fee": "1000",
        }
        respx.post(f"{BASE_URL}/v1/withdraws/krw").mock(
            return_value=httpx.Response(200, json=mock_krw_withdrawal)
        )

        with UpbitClient(access_key="access", secret_key="secret") as client:
            service = client.withdrawal
            result = service.withdraw_krw(amount=Decimal("100000"))

        assert isinstance(result, Withdrawal)
        assert result.currency == "KRW"
        assert result.amount == Decimal("100000")


class TestAsyncWithdrawalService:
    """Tests for asynchronous withdrawal service."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_get_withdrawals(self) -> None:
        """Test async get_withdrawals."""
        respx.get(f"{BASE_URL}/v1/withdraws").mock(
            return_value=httpx.Response(200, json=MOCK_WITHDRAWALS_LIST)
        )

        async with AsyncUpbitClient(access_key="access", secret_key="secret") as client:
            service = client.withdrawal
            result = await service.get_withdrawals(currency="BTC")

        assert len(result) == 1
        assert isinstance(result[0], Withdrawal)

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_get_withdrawal_chance(self) -> None:
        """Test async get_withdrawal_chance."""
        respx.get(f"{BASE_URL}/v1/withdraws/chance").mock(
            return_value=httpx.Response(200, json=MOCK_WITHDRAWAL_CHANCE)
        )

        async with AsyncUpbitClient(access_key="access", secret_key="secret") as client:
            service = client.withdrawal
            result = await service.get_withdrawal_chance(currency="BTC")

        assert isinstance(result, WithdrawalChance)
        assert result.currency.code == "BTC"
