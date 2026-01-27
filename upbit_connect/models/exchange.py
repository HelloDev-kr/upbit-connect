"""Exchange API models for Upbit.

This module contains Pydantic V2 models for Exchange API endpoints including:
- Asset: Account balance information
- Order: Order information
- OrderRequest: Order creation request
- OrderSide: Buy/Sell enumeration
- OrderType: Order type enumeration (limit/price/market)
- APIKey: API key information and permissions
"""
# ruff: noqa: PLR0912, PLR2004

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class OrderSide(str, Enum):
    """Order side enumeration."""

    BID = "bid"  # Buy
    ASK = "ask"  # Sell


class OrderType(str, Enum):
    """Order type enumeration."""

    LIMIT = "limit"  # 지정가
    PRICE = "price"  # 시장가 매수 (buy with total price)
    MARKET = "market"  # 시장가 매도 (sell with volume)


class Asset(BaseModel):
    """Account asset information (계좌 정보).

    Represents the balance information for a specific currency in the user's account.
    """

    currency: str = Field(..., description="Currency code (e.g., KRW, BTC)")
    balance: Decimal = Field(..., description="Total available balance")
    locked: Decimal = Field(..., description="Balance locked in orders")
    avg_buy_price: Decimal = Field(..., description="Average buy price")
    avg_buy_price_modified: bool = Field(..., description="Whether average buy price was modified")
    unit_currency: str = Field(..., description="Unit currency (e.g., KRW)")

    @field_validator("balance", "locked", "avg_buy_price", mode="before")
    @classmethod
    def parse_decimal(cls, v: str | float | Decimal) -> Decimal:
        """Parse string/float values to Decimal for financial precision."""
        if isinstance(v, str):
            return Decimal(v)
        if isinstance(v, float):
            return Decimal(str(v))
        return v


class APIKey(BaseModel):
    """API key information and permissions (API 키 정보).

    Represents an active API key, its expiration, and granted permissions.
    """

    access_key: str = Field(..., description="Access key")
    expire_at: datetime = Field(..., description="Expiration time")
    permissions: list[str] = Field(..., description="List of granted permissions")


class Order(BaseModel):
    """Order information (주문 정보).

    Represents a single order with complete state information.
    """

    uuid: str = Field(..., description="Order UUID")
    side: OrderSide = Field(..., description="Order side (bid/ask)")
    ord_type: OrderType = Field(..., description="Order type")
    price: Decimal | None = Field(None, description="Order price (null for market orders)")
    state: str = Field(..., description="Order state (wait/watch/done/cancel)")
    market: str = Field(..., description="Market code (e.g., KRW-BTC)")
    created_at: datetime = Field(..., description="Order creation time")
    volume: Decimal | None = Field(None, description="Order volume")
    remaining_volume: Decimal | None = Field(None, description="Remaining volume to be executed")
    reserved_fee: Decimal = Field(..., description="Reserved fee for this order")
    remaining_fee: Decimal = Field(..., description="Remaining fee")
    paid_fee: Decimal = Field(..., description="Paid fee")
    locked: Decimal = Field(..., description="Locked amount for this order")
    executed_volume: Decimal = Field(..., description="Executed volume")
    trades_count: int = Field(..., description="Number of trades executed")

    @field_validator(
        "price",
        "volume",
        "remaining_volume",
        "reserved_fee",
        "remaining_fee",
        "paid_fee",
        "locked",
        "executed_volume",
        mode="before",
    )
    @classmethod
    def parse_decimal(cls, v: str | float | Decimal | None) -> Decimal | None:
        """Parse string/float values to Decimal for financial precision."""
        if v is None:
            return None
        if isinstance(v, str):
            return Decimal(v)
        if isinstance(v, float):
            return Decimal(str(v))
        return v


class OrderRequest(BaseModel):
    """Order creation request (주문 요청).

    Used to create new orders on the exchange.

    Examples:
        # Limit buy order
        OrderRequest(market="KRW-BTC", side=OrderSide.BID, ord_type=OrderType.LIMIT,
                     price=Decimal("50000000"), volume=Decimal("0.1"))

        # Market buy order (by total price)
        OrderRequest(market="KRW-BTC", side=OrderSide.BID, ord_type=OrderType.PRICE,
                     price=Decimal("100000"))

        # Market sell order (by volume)
        OrderRequest(market="KRW-BTC", side=OrderSide.ASK, ord_type=OrderType.MARKET,
                     volume=Decimal("0.1"))
    """

    market: str = Field(..., description="Market code (e.g., KRW-BTC)")
    side: OrderSide = Field(..., description="Order side (bid/ask)")
    ord_type: OrderType = Field(..., description="Order type")
    price: Decimal | None = Field(None, description="Order price (required for limit orders)")
    volume: Decimal | None = Field(None, description="Order volume")

    @field_validator("price", "volume", mode="before")
    @classmethod
    def parse_decimal(cls, v: str | float | Decimal | None) -> Decimal | None:
        """Parse string/float values to Decimal for financial precision."""
        if v is None:
            return None
        if isinstance(v, str):
            return Decimal(v)
        if isinstance(v, float):
            return Decimal(str(v))
        return v


def validate_price_tick(market: str, price: Decimal) -> bool:
    """Validates price against market tick size rules.

    Args:
        market: Market code (e.g., "KRW-BTC")
        price: Order price

    Returns:
        True if price matches tick size requirements

    Example tick rules for KRW markets:
        price >= 2,000,000: 1,000 KRW units
        price >= 1,000,000: 500 KRW units
        price >= 500,000: 100 KRW units
        price >= 100,000: 50 KRW units
        price >= 10,000: 10 KRW units
        price >= 1,000: 5 KRW units
        price >= 100: 1 KRW units
        price < 100: 0.1 KRW units

    Note:
        Currently implements KRW market tick size rules.
        Other quote currencies (BTC, USDT) have different rules.
    """
    # Extract quote currency from market (e.g., "KRW" from "KRW-BTC")
    quote_currency = market.split("-")[0]

    # KRW market tick size rules
    if quote_currency == "KRW":
        if price >= 2_000_000:
            tick_size = Decimal("1000")
        elif price >= 1_000_000:
            tick_size = Decimal("500")
        elif price >= 500_000:
            tick_size = Decimal("100")
        elif price >= 100_000:
            tick_size = Decimal("50")
        elif price >= 10_000:
            tick_size = Decimal("10")
        elif price >= 1_000:
            tick_size = Decimal("5")
        elif price >= 100:
            tick_size = Decimal("1")
        else:
            tick_size = Decimal("0.1")

        # Check if price is a multiple of tick_size
        return price % tick_size == 0

    # BTC market tick size rules (satoshi = 0.00000001 BTC)
    elif quote_currency == "BTC":
        tick_size = Decimal("0.00000001")
        return price % tick_size == 0

    # USDT market tick size rules
    elif quote_currency == "USDT":
        if price >= 1000:
            tick_size = Decimal("1")
        elif price >= 100:
            tick_size = Decimal("0.1")
        elif price >= 10:
            tick_size = Decimal("0.01")
        elif price >= 1:
            tick_size = Decimal("0.001")
        else:
            tick_size = Decimal("0.0001")

        return price % tick_size == 0

    # Unknown quote currency - assume valid
    return True
