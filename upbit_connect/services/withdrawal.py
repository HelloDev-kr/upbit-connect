"""Withdrawal API service for Upbit.

This module provides service classes for Upbit Withdrawal API endpoints:
- Withdrawal list and individual inquiry
- Withdrawal chance inquiry
- Digital asset (coin) withdrawal request
- KRW withdrawal request
"""

from decimal import Decimal
from typing import Any

from upbit_connect._client_base import AsyncRequester, SyncRequester
from upbit_connect.models.withdrawal import Withdrawal, WithdrawalChance


class WithdrawalService:
    """Synchronous service for Upbit Withdrawal API endpoints.

    All methods require authentication (access_key/secret_key).

    Attributes:
        client: Requester instance with auth configured.
    """

    def __init__(self, client: SyncRequester) -> None:
        """Initialize the withdrawal service.

        Args:
            client: Requester instance with auth configured.
        """
        self.client = client

    def get_withdrawals(  # noqa: PLR0913
        self,
        currency: str | None = None,
        state: str | None = None,
        uuids: list[str] | None = None,
        txids: list[str] | None = None,
        limit: int = 100,
        page: int = 1,
        order_by: str = "desc",
    ) -> list[Withdrawal]:
        """Get a list of withdrawals with optional filters.

        Args:
            currency: Currency code (e.g., "KRW", "BTC").
            state: Withdrawal state.
            uuids: List of withdrawal UUIDs.
            txids: List of withdrawal TXIDs.
            limit: Records per page.
            page: Page number.
            order_by: Sorting order.

        Returns:
            List of Withdrawal models.
        """
        params = self.client._prepare_params(
            currency=currency,
            state=state,
            limit=limit,
            page=page,
            order_by=order_by,
            **{"uuids[]": uuids, "txids[]": txids},
        )

        response = self.client._get("/v1/withdraws", params=params)
        data: list[dict[str, Any]] = response.json()
        return [Withdrawal(**item) for item in data]

    def get_withdrawal(
        self,
        uuid: str | None = None,
        txid: str | None = None,
        currency: str | None = None,
    ) -> Withdrawal:
        """Get a single withdrawal by UUID, TXID, or currency.

        Args:
            uuid: Withdrawal UUID.
            txid: Withdrawal TXID.
            currency: Currency code.

        Returns:
            Withdrawal information.
        """
        params = self.client._prepare_params(uuid=uuid, txid=txid, currency=currency)
        response = self.client._get("/v1/withdraw", params=params)
        data: dict[str, Any] = response.json()
        return Withdrawal(**data)

    def get_withdrawal_chance(self, currency: str) -> WithdrawalChance:
        """Check withdrawal limits and availability for a currency.

        Args:
            currency: Currency code (e.g., "KRW", "BTC").

        Returns:
            WithdrawalChance model with limits and balance information.
        """
        params = self.client._prepare_params(currency=currency)
        response = self.client._get("/v1/withdraws/chance", params=params)
        data: dict[str, Any] = response.json()
        return WithdrawalChance(**data)

    def withdraw(  # noqa: PLR0913
        self,
        currency: str,
        amount: Decimal,
        address: str,
        secondary_address: str | None = None,
        net_type: str | None = None,
        transaction_type: str = "default",
    ) -> Withdrawal:
        """Request a digital asset (coin) withdrawal.

        Args:
            currency: Currency code.
            amount: Amount to withdraw.
            address: Destination address.
            secondary_address: Secondary address.
            net_type: Network type.
            transaction_type: Transaction type.

        Returns:
            Created Withdrawal information.
        """
        body = self.client._prepare_params(
            currency=currency,
            amount=amount,
            address=address,
            transaction_type=transaction_type,
            secondary_address=secondary_address,
            net_type=net_type,
        )

        response = self.client._post("/v1/withdraws/coin", body=body)
        data: dict[str, Any] = response.json()
        return Withdrawal(**data)

    def withdraw_krw(self, amount: Decimal) -> Withdrawal:
        """Request a KRW withdrawal.

        Args:
            amount: Amount of KRW to withdraw.

        Returns:
            Created Withdrawal information (KRW type).
        """
        body = self.client._prepare_params(amount=amount)
        response = self.client._post("/v1/withdraws/krw", body=body)
        data: dict[str, Any] = response.json()
        return Withdrawal(**data)


class AsyncWithdrawalService:
    """Asynchronous service for Upbit Withdrawal API endpoints.

    All methods require authentication (access_key/secret_key).

    Attributes:
        client: Requester instance with auth configured.
    """

    def __init__(self, client: AsyncRequester) -> None:
        """Initialize the async withdrawal service.

        Args:
            client: Requester instance with auth configured.
        """
        self.client = client

    async def get_withdrawals(  # noqa: PLR0913
        self,
        currency: str | None = None,
        state: str | None = None,
        uuids: list[str] | None = None,
        txids: list[str] | None = None,
        limit: int = 100,
        page: int = 1,
        order_by: str = "desc",
    ) -> list[Withdrawal]:
        """Get a list of withdrawals with optional filters.

        Args:
            currency: Currency code.
            state: Withdrawal state.
            uuids: List of withdrawal UUIDs.
            txids: List of withdrawal TXIDs.
            limit: Records per page.
            page: Page number.
            order_by: Sorting order.

        Returns:
            List of Withdrawal models.
        """
        params = self.client._prepare_params(
            currency=currency,
            state=state,
            limit=limit,
            page=page,
            order_by=order_by,
            **{"uuids[]": uuids, "txids[]": txids},
        )

        response = await self.client._get("/v1/withdraws", params=params)
        data: list[dict[str, Any]] = response.json()
        return [Withdrawal(**item) for item in data]

    async def get_withdrawal(
        self,
        uuid: str | None = None,
        txid: str | None = None,
        currency: str | None = None,
    ) -> Withdrawal:
        """Get a single withdrawal by UUID, TXID, or currency.

        Args:
            uuid: Withdrawal UUID.
            txid: Withdrawal TXID.
            currency: Currency code.

        Returns:
            Withdrawal information.
        """
        params = self.client._prepare_params(uuid=uuid, txid=txid, currency=currency)
        response = await self.client._get("/v1/withdraw", params=params)
        data: dict[str, Any] = response.json()
        return Withdrawal(**data)

    async def get_withdrawal_chance(self, currency: str) -> WithdrawalChance:
        """Check withdrawal limits and availability for a currency.

        Args:
            currency: Currency code.

        Returns:
            WithdrawalChance model.
        """
        params = self.client._prepare_params(currency=currency)
        response = await self.client._get("/v1/withdraws/chance", params=params)
        data: dict[str, Any] = response.json()
        return WithdrawalChance(**data)

    async def withdraw(  # noqa: PLR0913
        self,
        currency: str,
        amount: Decimal,
        address: str,
        secondary_address: str | None = None,
        net_type: str | None = None,
        transaction_type: str = "default",
    ) -> Withdrawal:
        """Request a digital asset (coin) withdrawal.

        Args:
            currency: Currency code.
            amount: Amount to withdraw.
            address: Destination address.
            secondary_address: Secondary address.
            net_type: Network type.
            transaction_type: Transaction type.

        Returns:
            Created Withdrawal information.
        """
        body = self.client._prepare_params(
            currency=currency,
            amount=amount,
            address=address,
            transaction_type=transaction_type,
            secondary_address=secondary_address,
            net_type=net_type,
        )

        response = await self.client._post("/v1/withdraws/coin", body=body)
        data: dict[str, Any] = response.json()
        return Withdrawal(**data)

    async def withdraw_krw(self, amount: Decimal) -> Withdrawal:
        """Request a KRW withdrawal.

        Args:
            amount: Amount of KRW to withdraw.

        Returns:
            Created Withdrawal information.
        """
        body = self.client._prepare_params(amount=amount)
        response = await self.client._post("/v1/withdraws/krw", body=body)
        data: dict[str, Any] = response.json()
        return Withdrawal(**data)
