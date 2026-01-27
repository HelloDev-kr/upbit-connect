"""Exchange API service for Upbit trading operations.

This module provides service classes for Upbit Exchange API endpoints:
- Account balance queries
- Order placement (limit, market buy, market sell)
- Order lookup and cancellation
- Price tick size validation

All methods require authentication (access_key/secret_key).
"""

from decimal import Decimal
from typing import Any

from upbit_connect._client_base import AsyncRequester, SyncRequester
from upbit_connect.exceptions import UpbitValidationError
from upbit_connect.models.exchange import (
    APIKey,
    Asset,
    Order,
    OrderSide,
    OrderType,
    validate_price_tick,
)


class ExchangeService:
    """Synchronous service for Upbit Exchange (trading) API endpoints.

    All methods require authentication (access_key/secret_key).

    Attributes:
        client: Requester instance with auth configured.
    """

    def __init__(self, client: SyncRequester) -> None:
        """Initialize the exchange service.

        Args:
            client: Requester instance with auth configured.
        """
        self.client = client

    def get_accounts(self) -> list[Asset]:
        """Get account balances for all currencies.

        Returns:
            List of Asset models with balance information.
        """
        response = self.client._get("/v1/accounts")
        data: list[dict[str, Any]] = response.json()
        return [Asset(**item) for item in data]

    def get_api_keys(self) -> list[APIKey]:
        """Get information about active API keys and their permissions.

        Returns:
            List of APIKey models.
        """
        response = self.client._get("/v1/api_keys")
        data: list[dict[str, Any]] = response.json()
        return [APIKey(**item) for item in data]

    def place_order(
        self,
        market: str,
        side: OrderSide,
        ord_type: OrderType,
        price: Decimal | None = None,
        volume: Decimal | None = None,
    ) -> Order:
        """Place a new order (generic method).

        Args:
            market: Market code (e.g., "KRW-BTC").
            side: Order side - BID (buy) or ASK (sell).
            ord_type: Order type.
            price: Order price.
            volume: Order volume.

        Returns:
            Created Order.
        """
        body = self.client._prepare_params(
            market=market,
            side=side.value,
            ord_type=ord_type.value,
            price=price,
            volume=volume,
        )

        response = self.client._post("/v1/orders", body=body)
        data: dict[str, Any] = response.json()
        return Order(**data)

    def get_order(
        self,
        uuid: str | None = None,
        identifier: str | None = None,
    ) -> Order:
        """Get a single order by UUID or identifier.

        Args:
            uuid: Order UUID.
            identifier: Client-provided order identifier.

        Returns:
            Order information.
        """
        self.client._validate_uuid_identifier(uuid, identifier)
        params = self.client._prepare_params(uuid=uuid, identifier=identifier)
        response = self.client._get("/v1/order", params=params)
        data: dict[str, Any] = response.json()
        return Order(**data)

    def get_orders(
        self,
        market: str | None = None,
        state: str | None = None,
        states: list[str] | None = None,
    ) -> list[Order]:
        """Get a list of orders with optional filters.

        Args:
            market: Filter by market code.
            state: Filter by single state.
            states: Filter by multiple states.

        Returns:
            List of Order models.
        """
        params = self.client._prepare_params(market=market, state=state, **{"states[]": states})
        response = self.client._get("/v1/orders", params=params)
        data: list[dict[str, Any]] = response.json()
        return [Order(**item) for item in data]

    def cancel_order(
        self,
        uuid: str | None = None,
        identifier: str | None = None,
    ) -> Order:
        """Cancel an order by UUID or identifier.

        Args:
            uuid: Order UUID.
            identifier: Client-provided order identifier.

        Returns:
            Cancelled Order information.
        """
        self.client._validate_uuid_identifier(uuid, identifier)
        params = self.client._prepare_params(uuid=uuid, identifier=identifier)
        response = self.client._delete("/v1/order", params=params)
        data: dict[str, Any] = response.json()
        return Order(**data)

    def buy_limit(self, market: str, price: Decimal, volume: Decimal) -> Order:
        """Place a limit buy order."""
        if not validate_price_tick(market, price):
            raise UpbitValidationError(f"Price {price} doesn't match tick size for {market}")

        return self.place_order(
            market=market,
            side=OrderSide.BID,
            ord_type=OrderType.LIMIT,
            price=price,
            volume=volume,
        )

    def sell_limit(self, market: str, price: Decimal, volume: Decimal) -> Order:
        """Place a limit sell order."""
        if not validate_price_tick(market, price):
            raise UpbitValidationError(f"Price {price} doesn't match tick size for {market}")

        return self.place_order(
            market=market,
            side=OrderSide.ASK,
            ord_type=OrderType.LIMIT,
            price=price,
            volume=volume,
        )

    def buy_market(self, market: str, price: Decimal) -> Order:
        """Place a market buy order."""
        return self.place_order(
            market=market,
            side=OrderSide.BID,
            ord_type=OrderType.PRICE,
            price=price,
        )

    def sell_market(self, market: str, volume: Decimal) -> Order:
        """Place a market sell order."""
        return self.place_order(
            market=market,
            side=OrderSide.ASK,
            ord_type=OrderType.MARKET,
            volume=volume,
        )


class AsyncExchangeService:
    """Asynchronous service for Upbit Exchange (trading) API endpoints.

    All methods require authentication (access_key/secret_key).

    Attributes:
        client: Requester instance with auth configured.
    """

    def __init__(self, client: AsyncRequester) -> None:
        """Initialize the async exchange service.

        Args:
            client: Requester instance with auth configured.
        """
        self.client = client

    async def get_accounts(self) -> list[Asset]:
        """Get account balances for all currencies.

        Returns:
            List of Asset models with balance information.
        """
        response = await self.client._get("/v1/accounts")
        data: list[dict[str, Any]] = response.json()
        return [Asset(**item) for item in data]

    async def get_api_keys(self) -> list[APIKey]:
        """Get information about active API keys and their permissions.

        Returns:
            List of APIKey models.
        """
        response = await self.client._get("/v1/api_keys")
        data: list[dict[str, Any]] = response.json()
        return [APIKey(**item) for item in data]

    async def place_order(
        self,
        market: str,
        side: OrderSide,
        ord_type: OrderType,
        price: Decimal | None = None,
        volume: Decimal | None = None,
    ) -> Order:
        """Place a new order (generic method).

        Args:
            market: Market code.
            side: Order side.
            ord_type: Order type.
            price: Order price.
            volume: Order volume.

        Returns:
            Created Order.
        """
        body = self.client._prepare_params(
            market=market,
            side=side.value,
            ord_type=ord_type.value,
            price=price,
            volume=volume,
        )

        response = await self.client._post("/v1/orders", body=body)
        data: dict[str, Any] = response.json()
        return Order(**data)

    async def get_order(
        self,
        uuid: str | None = None,
        identifier: str | None = None,
    ) -> Order:
        """Get a single order by UUID or identifier.

        Args:
            uuid: Order UUID.
            identifier: Client-provided order identifier.

        Returns:
            Order information.
        """
        self.client._validate_uuid_identifier(uuid, identifier)
        params = self.client._prepare_params(uuid=uuid, identifier=identifier)
        response = await self.client._get("/v1/order", params=params)
        data: dict[str, Any] = response.json()
        return Order(**data)

    async def get_orders(
        self,
        market: str | None = None,
        state: str | None = None,
        states: list[str] | None = None,
    ) -> list[Order]:
        """Get a list of orders with optional filters.

        Args:
            market: Filter by market code.
            state: Filter by single state.
            states: Filter by multiple states.

        Returns:
            List of Order models.
        """
        params = self.client._prepare_params(market=market, state=state, **{"states[]": states})
        response = await self.client._get("/v1/orders", params=params)
        data: list[dict[str, Any]] = response.json()
        return [Order(**item) for item in data]

    async def cancel_order(
        self,
        uuid: str | None = None,
        identifier: str | None = None,
    ) -> Order:
        """Cancel an order by UUID or identifier.

        Args:
            uuid: Order UUID.
            identifier: Client-provided order identifier.

        Returns:
            Cancelled Order information.
        """
        self.client._validate_uuid_identifier(uuid, identifier)
        params = self.client._prepare_params(uuid=uuid, identifier=identifier)
        response = await self.client._delete("/v1/order", params=params)
        data: dict[str, Any] = response.json()
        return Order(**data)

    async def buy_limit(self, market: str, price: Decimal, volume: Decimal) -> Order:
        """Place a limit buy order."""
        if not validate_price_tick(market, price):
            raise UpbitValidationError(f"Price {price} doesn't match tick size for {market}")

        return await self.place_order(
            market=market,
            side=OrderSide.BID,
            ord_type=OrderType.LIMIT,
            price=price,
            volume=volume,
        )

    async def sell_limit(self, market: str, price: Decimal, volume: Decimal) -> Order:
        """Place a limit sell order."""
        if not validate_price_tick(market, price):
            raise UpbitValidationError(f"Price {price} doesn't match tick size for {market}")

        return await self.place_order(
            market=market,
            side=OrderSide.ASK,
            ord_type=OrderType.LIMIT,
            price=price,
            volume=volume,
        )

    async def buy_market(self, market: str, price: Decimal) -> Order:
        """Place a market buy order."""
        return await self.place_order(
            market=market,
            side=OrderSide.BID,
            ord_type=OrderType.PRICE,
            price=price,
        )

    async def sell_market(self, market: str, volume: Decimal) -> Order:
        """Place a market sell order."""
        return await self.place_order(
            market=market,
            side=OrderSide.ASK,
            ord_type=OrderType.MARKET,
            volume=volume,
        )
