"""Example: Real-time data streaming using WebSocket.

This example demonstrates subscribing to ticker, orderbook, and trade channels
for live market data updates.
"""

import asyncio
import uuid
from typing import Any

import upbit_connect as upbit


async def handle_message(data: Any) -> None:
    """Process incoming WebSocket messages.

    Args:
        data: Parsed message data
    """
    if hasattr(data, "model_dump"):
        data = data.model_dump()

    if not isinstance(data, dict):
        return

    msg_type = data.get("type")

    if msg_type == "ticker":
        print(
            f"[TICKER] {data['code']}: {data['trade_price']:,} KRW "
            f"({data['signed_change_rate'] * 100:+.2f}%)"
        )
    elif msg_type == "orderbook":
        print(f"[ORDERBOOK] {data['code']}: Ask={len(data['orderbook_units'])} levels")
    elif msg_type == "trade":
        print(
            f"[TRADE] {data['code']}: "
            f"{data['trade_volume']} @ {data['trade_price']:,} KRW "
            f"({data['ask_bid'].upper()})"
        )


async def main() -> None:
    """Stream real-time market data via WebSocket."""
    ws = upbit.UpbitWebSocket()

    try:
        # Connect to WebSocket
        print("🔌 Connecting to Upbit WebSocket...")
        await ws.connect()
        print("✅ Connected!\n")

        # Subscribe to channels
        ticket = str(uuid.uuid4())
        channels = [
            {"type": "ticker", "codes": ["KRW-BTC", "KRW-ETH"]},
            {"type": "trade", "codes": ["KRW-BTC"]},
        ]

        await ws.subscribe(ticket, channels)
        print("📡 Subscribed to ticker and trade channels")
        print("Press Ctrl+C to stop\n")

        # Run event loop
        await ws.run(handle_message)

    except KeyboardInterrupt:
        print("\n\n🛑 Stopping...")
    finally:
        await ws.close()
        print("✅ Disconnected")


if __name__ == "__main__":
    asyncio.run(main())
