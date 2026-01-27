"""Example: Trading operations using Upbit Connect.

This example demonstrates account management and order placement.
Requires API keys with trading permissions.

⚠️  WARNING: This example uses real API calls. Use with caution!
"""

import asyncio
import os

import upbit_connect as upbit


async def main() -> None:
    """Demonstrate trading operations."""
    # Load credentials from environment
    access_key = os.getenv("UPBIT_ACCESS_KEY")
    secret_key = os.getenv("UPBIT_SECRET_KEY")

    if not access_key or not secret_key:
        print("❌ Error: Set UPBIT_ACCESS_KEY and UPBIT_SECRET_KEY environment variables")
        return

    async with upbit.AsyncUpbitClient(access_key=access_key, secret_key=secret_key) as client:
        # Get account balances
        print("💼 Account Balances:")
        accounts = await client.exchange.get_accounts()
        for account in accounts:
            if float(account.balance) > 0:
                print(f"{account.currency}: {account.balance} (locked: {account.locked})")

        # Example: Place a limit buy order (COMMENTED OUT FOR SAFETY)
        # market = "KRW-BTC"
        # price = Decimal("50000000")  # 50M KRW per BTC
        # volume = Decimal("0.001")     # Buy 0.001 BTC
        #
        # print(f"\n📝 Placing limit buy order...")
        # order = await client.exchange.buy_limit(market, price, volume)
        # print(f"Order placed: {order.uuid}")
        # print(f"Status: {order.state}")

        # Get open orders
        print("\n📋 Open Orders:")
        orders = await client.exchange.get_orders(state="wait")
        if orders:
            for order in orders[:5]:  # Show first 5
                print(f"{order.market} {order.side.value.upper()}: {order.price} x {order.volume}")
        else:
            print("No open orders")


if __name__ == "__main__":
    asyncio.run(main())
