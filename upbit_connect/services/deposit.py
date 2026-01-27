"""Deposit API service for Upbit.

This module provides service classes for Upbit Deposit API endpoints:
- Deposit list and individual inquiry
- Deposit address generation and inquiry
- KRW deposit request
"""

from decimal import Decimal
from typing import Any

from upbit_connect._client_base import AsyncRequester, SyncRequester
from upbit_connect.models.deposit import Deposit, DepositAddress


class DepositService:
    """Synchronous service for Upbit Deposit API endpoints.

    All methods require authentication (access_key/secret_key).

    Attributes:
        client: Requester instance with auth configured.
    """

    def __init__(self, client: SyncRequester) -> None:
        """Initialize the deposit service.

        Args:
            client: Requester instance with auth configured.
        """
        self.client = client

    def get_deposits(  # noqa: PLR0913
        self,
        currency: str | None = None,
        state: str | None = None,
        uuids: list[str] | None = None,
        txids: list[str] | None = None,
        limit: int = 100,
        page: int = 1,
        order_by: str = "desc",
    ) -> list[Deposit]:
        """Get a list of deposits with optional filters.

        Args:
            currency: Currency code (e.g., "KRW", "BTC").
            state: Deposit state.
            uuids: List of deposit UUIDs.
            txids: List of deposit TXIDs.
            limit: Records per page.
            page: Page number.
            order_by: Sorting order.

        Returns:
            List of Deposit models.
        """
        params = self.client._prepare_params(
            currency=currency,
            state=state,
            limit=limit,
            page=page,
            order_by=order_by,
            **{"uuids[]": uuids, "txids[]": txids},
        )

        response = self.client._get("/v1/deposits", params=params)
        data: list[dict[str, Any]] = response.json()
        return [Deposit(**item) for item in data]

    def get_deposit(
        self,
        uuid: str | None = None,
        txid: str | None = None,
        currency: str | None = None,
    ) -> Deposit:
        """Get a single deposit by UUID, TXID, or currency.

        Args:
            uuid: Deposit UUID.
            txid: Deposit TXID.
            currency: Currency code.

        Returns:
            Deposit information.
        """
        params = self.client._prepare_params(uuid=uuid, txid=txid, currency=currency)
        response = self.client._get("/v1/deposit", params=params)
        data: dict[str, Any] = response.json()
        return Deposit(**data)

    def generate_deposit_address(
        self, currency: str, net_type: str | None = None
    ) -> DepositAddress:
        """Create a new deposit address for a currency.

        Args:
            currency: Currency code.
            net_type: Network type.

        Returns:
            Created DepositAddress information.
        """
        body = self.client._prepare_params(currency=currency, net_type=net_type)
        response = self.client._post("/v1/deposits/generate_coin_address", body=body)
        data: dict[str, Any] = response.json()
        return DepositAddress(**data)

    def get_deposit_addresses(self) -> list[DepositAddress]:
        """List all deposit addresses for the account.

        Returns:
            List of DepositAddress models.
        """
        response = self.client._get("/v1/deposits/coin_addresses")
        data: list[dict[str, Any]] = response.json()
        return [DepositAddress(**item) for item in data]

    def get_deposit_address(self, currency: str, net_type: str | None = None) -> DepositAddress:
        """Get a specific deposit address.

        Args:
            currency: Currency code.
            net_type: Network type.

        Returns:
            DepositAddress information.
        """
        params = self.client._prepare_params(currency=currency, net_type=net_type)
        response = self.client._get("/v1/deposits/coin_address", params=params)
        data: dict[str, Any] = response.json()
        return DepositAddress(**data)

    def deposit_krw(self, amount: Decimal) -> Deposit:
        """Request a KRW deposit.

        Args:
            amount: Amount of KRW to deposit.

        Returns:
            Created Deposit information (KRW type).
        """
        body = self.client._prepare_params(amount=amount)
        response = self.client._post("/v1/deposits/krw", body=body)
        data: dict[str, Any] = response.json()
        return Deposit(**data)


class AsyncDepositService:
    """Asynchronous service for Upbit Deposit API endpoints.

    All methods require authentication (access_key/secret_key).

    Attributes:
        client: Requester instance with auth configured.
    """

    def __init__(self, client: AsyncRequester) -> None:
        """Initialize the async deposit service.

        Args:
            client: Requester instance with auth configured.
        """
        self.client = client

    async def get_deposits(  # noqa: PLR0913
        self,
        currency: str | None = None,
        state: str | None = None,
        uuids: list[str] | None = None,
        txids: list[str] | None = None,
        limit: int = 100,
        page: int = 1,
        order_by: str = "desc",
    ) -> list[Deposit]:
        """Get a list of deposits with optional filters.

        Args:
            currency: Currency code.
            state: Deposit state.
            uuids: List of deposit UUIDs.
            txids: List of deposit TXIDs.
            limit: Records per page.
            page: Page number.
            order_by: Sorting order.

        Returns:
            List of Deposit models.
        """
        params = self.client._prepare_params(
            currency=currency,
            state=state,
            limit=limit,
            page=page,
            order_by=order_by,
            **{"uuids[]": uuids, "txids[]": txids},
        )

        response = await self.client._get("/v1/deposits", params=params)
        data: list[dict[str, Any]] = response.json()
        return [Deposit(**item) for item in data]

    async def get_deposit(
        self,
        uuid: str | None = None,
        txid: str | None = None,
        currency: str | None = None,
    ) -> Deposit:
        """Get a single deposit by UUID, TXID, or currency.

        Args:
            uuid: Deposit UUID.
            txid: Deposit TXID.
            currency: Currency code.

        Returns:
            Deposit information.
        """
        params = self.client._prepare_params(uuid=uuid, txid=txid, currency=currency)
        response = await self.client._get("/v1/deposit", params=params)
        data: dict[str, Any] = response.json()
        return Deposit(**data)

    async def generate_deposit_address(
        self, currency: str, net_type: str | None = None
    ) -> DepositAddress:
        """Create a new deposit address for a currency.

        Args:
            currency: Currency code.
            net_type: Network type.

        Returns:
            Created DepositAddress information.
        """
        body = self.client._prepare_params(currency=currency, net_type=net_type)
        response = await self.client._post("/v1/deposits/generate_coin_address", body=body)
        data: dict[str, Any] = response.json()
        return DepositAddress(**data)

    async def get_deposit_addresses(self) -> list[DepositAddress]:
        """List all deposit addresses for the account.

        Returns:
            List of DepositAddress models.
        """
        response = await self.client._get("/v1/deposits/coin_addresses")
        data: list[dict[str, Any]] = response.json()
        return [DepositAddress(**item) for item in data]

    async def get_deposit_address(
        self, currency: str, net_type: str | None = None
    ) -> DepositAddress:
        """Get a specific deposit address.

        Args:
            currency: Currency code.
            net_type: Network type.

        Returns:
            DepositAddress information.
        """
        params = self.client._prepare_params(currency=currency, net_type=net_type)
        response = await self.client._get("/v1/deposits/coin_address", params=params)
        data: dict[str, Any] = response.json()
        return DepositAddress(**data)

    async def deposit_krw(self, amount: Decimal) -> Deposit:
        """Request a KRW deposit.

        Args:
            amount: Amount of KRW to deposit.

        Returns:
            Created Deposit information.
        """
        body = self.client._prepare_params(amount=amount)
        response = await self.client._post("/v1/deposits/krw", body=body)
        data: dict[str, Any] = response.json()
        return Deposit(**data)
