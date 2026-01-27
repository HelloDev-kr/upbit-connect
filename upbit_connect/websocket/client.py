"""Async WebSocket client for Upbit real-time data.

This module provides WebSocket connectivity for real-time market data streaming:
- Public channels: ticker, orderbook, trade
- Private channels: myOrder, myAsset (requires authentication)

Features:
- Auto-reconnect on disconnect with exponential backoff
- Ping/pong handling via websockets library built-in support
- Automatic JSON to Pydantic model conversion
- Subscription management with re-subscription on reconnect
"""

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

import websockets
from websockets.asyncio.client import ClientConnection

from upbit_connect.auth import generate_jwt_token
from upbit_connect.exceptions import UpbitError
from upbit_connect.models.exchange import Asset, Order
from upbit_connect.models.quotation import Orderbook, Ticker, Trade

MessageCallback = Callable[
    [Ticker | Orderbook | Trade | Order | Asset | dict[str, Any]], Awaitable[None]
]


class UpbitWebSocket:
    """Async WebSocket client for Upbit real-time data.

    Supports both public (ticker, orderbook, trade) and private (myOrder, myAsset)
    channels with automatic reconnection on disconnect or ping timeout.

    Attributes:
        access_key: API access key (optional for public channels).
        secret_key: API secret key (optional for public channels).
        websocket: Active WebSocket connection.
        subscriptions: Currently subscribed channels with their tickets.
        running: Connection status flag.

    Example:
        # Public channels (no authentication needed)
        ws = UpbitWebSocket()
        await ws.connect()
        await ws.subscribe("my-ticket", [{"type": "ticker", "codes": ["KRW-BTC"]}])
        await ws.run(my_callback)

        # Private channels (authentication required)
        ws = UpbitWebSocket(access_key="...", secret_key="...")
        await ws.connect()
        await ws.subscribe("my-ticket", [{"type": "myOrder"}])
        await ws.run(my_callback)
    """

    WS_URL = "wss://api.upbit.com/websocket/v1"
    PING_INTERVAL: float = 30.0
    PING_TIMEOUT: float = 10.0
    RECONNECT_DELAY: float = 1.0
    MAX_RECONNECT_DELAY: float = 60.0

    def __init__(
        self,
        access_key: str | None = None,
        secret_key: str | None = None,
    ) -> None:
        """Initialize WebSocket client.

        Args:
            access_key: Upbit API access key (required for private channels).
            secret_key: Upbit API secret key (required for private channels).
        """
        self.access_key = access_key
        self.secret_key = secret_key
        self.websocket: ClientConnection | None = None
        self.subscriptions: list[tuple[str, list[dict[str, Any]]]] = []
        self.running = False
        self._reconnect_delay = self.RECONNECT_DELAY

    async def connect(self) -> None:
        """Establish WebSocket connection.

        Uses websockets library's built-in ping/pong handling for keepalive.

        Raises:
            UpbitError: If connection fails.
        """
        try:
            self.websocket = await websockets.connect(
                self.WS_URL,
                ping_interval=self.PING_INTERVAL,
                ping_timeout=self.PING_TIMEOUT,
            )
            self.running = True
            self._reconnect_delay = self.RECONNECT_DELAY
        except Exception as e:
            raise UpbitError(f"WebSocket connection failed: {e}") from e

    async def subscribe(
        self,
        ticket: str,
        channels: list[dict[str, Any]],
    ) -> None:
        """Subscribe to channels.

        Args:
            ticket: Unique subscription ticket (UUID recommended).
            channels: List of channel configurations.
                Example: [{"type": "ticker", "codes": ["KRW-BTC"]}]
                Available public types: ticker, orderbook, trade
                Available private types: myOrder, myAsset

        Raises:
            UpbitError: If not connected or subscription fails.

        Note:
            Private channels (myOrder, myAsset) require access_key and secret_key
            to be provided during client initialization.
        """
        if not self.websocket:
            raise UpbitError("Not connected to WebSocket")

        ticket_msg: dict[str, Any] = {"ticket": ticket}

        if self.access_key and self.secret_key:
            has_private_channel = any(ch.get("type") in ("myOrder", "myAsset") for ch in channels)
            if has_private_channel:
                auth_token = generate_jwt_token(self.access_key, self.secret_key, None, None)
                ticket_msg["auth"] = auth_token

        message: list[dict[str, Any]] = [ticket_msg]

        for channel in channels:
            channel_msg: dict[str, Any] = {"type": channel["type"]}
            if "codes" in channel:
                channel_msg["codes"] = channel["codes"]
            if "isOnlyRealtime" in channel:
                channel_msg["isOnlyRealtime"] = channel["isOnlyRealtime"]
            if "isOnlySnapshot" in channel:
                channel_msg["isOnlySnapshot"] = channel["isOnlySnapshot"]
            message.append(channel_msg)

        message.append({"format": "DEFAULT"})

        await self.websocket.send(json.dumps(message))
        self.subscriptions.append((ticket, channels))

    async def unsubscribe(
        self,
        ticket: str,
    ) -> None:
        """Unsubscribe from channels by ticket.

        Args:
            ticket: The ticket used when subscribing.

        Note:
            Upbit WebSocket doesn't support unsubscribe messages.
            This only removes the subscription from tracking.
            To fully unsubscribe, close and reconnect without that subscription.
        """
        self.subscriptions = [(t, ch) for t, ch in self.subscriptions if t != ticket]

    async def _resubscribe(self) -> None:
        """Re-subscribe to all tracked subscriptions after reconnect."""
        subs_to_restore = list(self.subscriptions)
        self.subscriptions = []

        for ticket, channels in subs_to_restore:
            await self.subscribe(ticket, channels)

    def _parse_message(
        self, data: dict[str, Any]
    ) -> Ticker | Orderbook | Trade | Order | Asset | dict[str, Any]:
        """Parse JSON message to appropriate Pydantic model.

        Args:
            data: Raw JSON data from WebSocket.

        Returns:
            Parsed Pydantic model or raw dict if type unknown.
        """
        msg_type = data.get("type")

        if msg_type == "ticker":
            return Ticker(**data)
        elif msg_type == "orderbook":
            return Orderbook(**data)
        elif msg_type == "trade":
            return Trade(**data)
        elif msg_type == "myOrder":
            return Order(**data)
        elif msg_type == "myAsset":
            return Asset(**data)
        else:
            return data

    async def run(
        self,
        callback: MessageCallback,
    ) -> None:
        """Run WebSocket event loop with auto-reconnect.

        Continuously receives messages and passes parsed models to callback.
        Automatically reconnects on disconnect with exponential backoff.

        Args:
            callback: Async function to handle received messages.
                Receives parsed Pydantic models (Ticker, Orderbook, Trade, Order, Asset)
                or raw dict for unknown message types.

        Raises:
            UpbitError: If unrecoverable error occurs.
        """
        while self.running:
            try:
                if not self.websocket:
                    await self.connect()
                    await self._resubscribe()

                if self.websocket is None:
                    continue

                async for message in self.websocket:
                    if isinstance(message, bytes):
                        data = json.loads(message.decode("utf-8"))
                    else:
                        data = json.loads(message)

                    parsed = self._parse_message(data)
                    await callback(parsed)

            except websockets.exceptions.ConnectionClosed:
                if self.running:
                    self.websocket = None
                    await asyncio.sleep(self._reconnect_delay)
                    self._reconnect_delay = min(self._reconnect_delay * 2, self.MAX_RECONNECT_DELAY)
            except asyncio.CancelledError:
                self.running = False
                raise
            except Exception as e:
                if self.running:
                    self.websocket = None
                    await asyncio.sleep(self._reconnect_delay)
                    self._reconnect_delay = min(self._reconnect_delay * 2, self.MAX_RECONNECT_DELAY)
                else:
                    raise UpbitError(f"WebSocket error: {e}") from e

    async def close(self) -> None:
        """Close WebSocket connection.

        Gracefully shuts down the connection and stops the run loop.
        """
        self.running = False
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
