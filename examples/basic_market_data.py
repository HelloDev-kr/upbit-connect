"""Example: Basic market data queries using Upbit Connect.

This example demonstrates how to fetch market information, tickers, and candles
using the Quotation API (no authentication required).
"""

import asyncio

import upbit_connect as upbit


async def main() -> None:
    """Fetch and display basic market data."""
    async with upbit.AsyncUpbitClient() as client:
        # Get all available markets
        print("📊 Fetching available markets...")
        markets = await client.quotation.get_markets()
        krw_markets = [m for m in markets if str(m.get("market", "")).startswith("KRW-")]
        print(f"Found {len(krw_markets)} KRW markets\n")

        # Get current price for BTC and ETH
        print("💰 Current Prices:")
        tickers = await client.quotation.get_ticker(["KRW-BTC", "KRW-ETH"])
        for ticker in tickers:
            print(f"{ticker.market}: {ticker.trade_price:,} KRW")
            print(f"  Change: {ticker.signed_change_rate * 100:.2f}%")
            print(f"  Volume (24h): {ticker.acc_trade_volume_24h:.4f}\n")

        # Get daily candles for BTC
        print("📈 BTC Daily Candles (Last 7 days):")
        candles = await client.quotation.get_candles_days("KRW-BTC", count=7)
        for candle in candles:
            print(
                f"{candle.candle_date_time_kst}: "
                f"Open={candle.opening_price:,} "
                f"High={candle.high_price:,} "
                f"Low={candle.low_price:,} "
                f"Close={candle.trade_price:,}"
            )


if __name__ == "__main__":
    asyncio.run(main())
