"""Quotation API response models for Upbit.

This module defines Pydantic V2 models for all Upbit Quotation API responses:
- Ticker (현재가 정보)
- Candle (캔들 차트 - minute/day/week/month)
- Orderbook (호가 정보)
- Trade (체결 정보)

All price and volume fields use Decimal for precision.
All timestamp fields are converted to datetime objects.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AskBid(str, Enum):
    """Trade ask/bid type."""

    ASK = "ASK"
    BID = "BID"


class ChangeType(str, Enum):
    """Price change type."""

    EVEN = "EVEN"  # 보합
    RISE = "RISE"  # 상승
    FALL = "FALL"  # 하락


class OrderbookUnit(BaseModel):
    """Single orderbook unit (호가 단위).

    Represents a single level in the orderbook with ask/bid prices and sizes.
    """

    model_config = ConfigDict(strict=True)

    ask_price: Decimal = Field(..., description="매도 호가")
    bid_price: Decimal = Field(..., description="매수 호가")
    ask_size: Decimal = Field(..., description="매도 잔량")
    bid_size: Decimal = Field(..., description="매수 잔량")

    @field_validator("ask_price", "bid_price", "ask_size", "bid_size", mode="before")
    @classmethod
    def parse_decimal(cls, v: str | float | Decimal | int) -> Decimal:
        """Parse string/float values to Decimal for financial precision."""
        if isinstance(v, (str, int)):
            return Decimal(str(v))
        if isinstance(v, float):
            return Decimal(str(v))
        return v


class Ticker(BaseModel):
    """Ticker (현재가) information.

    Current market data for a trading pair including price, volume, and change statistics.
    """

    model_config = ConfigDict(strict=True)

    market: str = Field(..., description="마켓 코드 (e.g., KRW-BTC)")
    trade_date: str = Field(..., description="최근 거래 일자 (YYYYMMDD)")
    trade_time: str = Field(..., description="최근 거래 시각 (HHMMSS)")
    trade_date_kst: str = Field(..., description="최근 거래 일자 KST (YYYYMMDD)")
    trade_time_kst: str = Field(..., description="최근 거래 시각 KST (HHMMSS)")
    trade_timestamp: datetime = Field(..., description="최근 거래 타임스탬프")
    opening_price: Decimal = Field(..., description="시가")
    high_price: Decimal = Field(..., description="고가")
    low_price: Decimal = Field(..., description="저가")
    trade_price: Decimal = Field(..., description="현재가")
    prev_closing_price: Decimal = Field(..., description="전일 종가")
    change: ChangeType = Field(..., description="전일 대비")
    change_price: Decimal = Field(..., description="전일 대비 가격 변화량")
    change_rate: Decimal = Field(..., description="전일 대비 변화율")
    signed_change_price: Decimal = Field(..., description="부호가 있는 변화액")
    signed_change_rate: Decimal = Field(..., description="부호가 있는 변화율")
    trade_volume: Decimal = Field(..., description="가장 최근 거래량")
    acc_trade_price: Decimal = Field(..., description="누적 거래대금 (UTC 0시 기준)")
    acc_trade_price_24h: Decimal = Field(..., description="24시간 누적 거래대금")
    acc_trade_volume: Decimal = Field(..., description="누적 거래량 (UTC 0시 기준)")
    acc_trade_volume_24h: Decimal = Field(..., description="24시간 누적 거래량")
    highest_52_week_price: Decimal = Field(..., description="52주 최고가")
    highest_52_week_date: str = Field(..., description="52주 최고가 달성일 (YYYY-MM-DD)")
    lowest_52_week_price: Decimal = Field(..., description="52주 최저가")
    lowest_52_week_date: str = Field(..., description="52주 최저가 달성일 (YYYY-MM-DD)")
    timestamp: datetime = Field(..., description="타임스탬프")

    @field_validator("change", mode="before")
    @classmethod
    def parse_change_type(cls, v: str | ChangeType) -> ChangeType:
        """Parse string to ChangeType enum."""
        if isinstance(v, str):
            return ChangeType(v)
        return v

    @field_validator(
        "opening_price",
        "high_price",
        "low_price",
        "trade_price",
        "prev_closing_price",
        "change_price",
        "change_rate",
        "signed_change_price",
        "signed_change_rate",
        "trade_volume",
        "acc_trade_price",
        "acc_trade_price_24h",
        "acc_trade_volume",
        "acc_trade_volume_24h",
        "highest_52_week_price",
        "lowest_52_week_price",
        mode="before",
    )
    @classmethod
    def parse_decimal(cls, v: str | float | Decimal | int) -> Decimal:
        """Parse string/float values to Decimal for financial precision."""
        if isinstance(v, (str, int)):
            return Decimal(str(v))
        if isinstance(v, float):
            return Decimal(str(v))
        return v

    @field_validator("trade_timestamp", "timestamp", mode="before")
    @classmethod
    def convert_timestamp(cls, v: int | datetime) -> datetime:
        """Convert Unix timestamp (milliseconds) to datetime.

        Args:
            v: Unix timestamp in milliseconds or datetime object

        Returns:
            datetime object
        """
        if isinstance(v, datetime):
            return v
        return datetime.fromtimestamp(v / 1000)


class CandleMinute(BaseModel):
    """Minute candle (분봉) data.

    OHLCV data for minute-interval candles (1/3/5/10/15/30/60/240 minutes).
    """

    model_config = ConfigDict(strict=True)

    market: str = Field(..., description="마켓 코드")
    candle_date_time_utc: datetime = Field(..., description="캔들 기준 시각 (UTC)")
    candle_date_time_kst: datetime = Field(..., description="캔들 기준 시각 (KST)")
    opening_price: Decimal = Field(..., description="시가")
    high_price: Decimal = Field(..., description="고가")
    low_price: Decimal = Field(..., description="저가")
    trade_price: Decimal = Field(..., description="종가")
    timestamp: datetime = Field(..., description="마지막 틱 타임스탬프")
    candle_acc_trade_price: Decimal = Field(..., description="누적 거래 금액")
    candle_acc_trade_volume: Decimal = Field(..., description="누적 거래량")
    unit: int = Field(..., description="분 단위 (1/3/5/10/15/30/60/240)")

    @field_validator(
        "opening_price",
        "high_price",
        "low_price",
        "trade_price",
        "candle_acc_trade_price",
        "candle_acc_trade_volume",
        mode="before",
    )
    @classmethod
    def parse_decimal(cls, v: str | float | Decimal | int) -> Decimal:
        """Parse string/float values to Decimal for financial precision."""
        if isinstance(v, (str, int)):
            return Decimal(str(v))
        if isinstance(v, float):
            return Decimal(str(v))
        return v

    @field_validator("candle_date_time_utc", "candle_date_time_kst", "timestamp", mode="before")
    @classmethod
    def convert_timestamp(cls, v: str | datetime) -> datetime:
        """Convert ISO 8601 string or timestamp to datetime.

        Args:
            v: ISO 8601 datetime string or datetime object

        Returns:
            datetime object
        """
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            # Handle ISO 8601 format: "2024-01-27T12:00:00"
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        # Handle Unix timestamp in milliseconds
        return datetime.fromtimestamp(v / 1000)


class CandleDay(BaseModel):
    """Day candle (일봉) data.

    OHLCV data for daily candles.
    """

    model_config = ConfigDict(strict=True)

    market: str = Field(..., description="마켓 코드")
    candle_date_time_utc: datetime = Field(..., description="캔들 기준 시각 (UTC 0시)")
    candle_date_time_kst: datetime = Field(..., description="캔들 기준 시각 (KST 9시)")
    opening_price: Decimal = Field(..., description="시가")
    high_price: Decimal = Field(..., description="고가")
    low_price: Decimal = Field(..., description="저가")
    trade_price: Decimal = Field(..., description="종가")
    timestamp: datetime = Field(..., description="마지막 틱 타임스탬프")
    candle_acc_trade_price: Decimal = Field(..., description="누적 거래 금액")
    candle_acc_trade_volume: Decimal = Field(..., description="누적 거래량")
    prev_closing_price: Decimal = Field(..., description="전일 종가 (UTC 0시 기준)")
    change_price: Decimal = Field(..., description="전일 종가 대비 변화 금액")
    change_rate: Decimal = Field(..., description="전일 종가 대비 변화율")
    converted_trade_price: Decimal | None = Field(
        None, description="종가 환산 화폐 단위로 환산된 가격 (if requested)"
    )

    @field_validator(
        "opening_price",
        "high_price",
        "low_price",
        "trade_price",
        "candle_acc_trade_price",
        "candle_acc_trade_volume",
        "prev_closing_price",
        "change_price",
        "change_rate",
        "converted_trade_price",
        mode="before",
    )
    @classmethod
    def parse_decimal(cls, v: str | float | Decimal | int | None) -> Decimal | None:
        """Parse string/float values to Decimal for financial precision."""
        if v is None:
            return None
        if isinstance(v, (str, int)):
            return Decimal(str(v))
        if isinstance(v, float):
            return Decimal(str(v))
        return v

    @field_validator("candle_date_time_utc", "candle_date_time_kst", "timestamp", mode="before")
    @classmethod
    def convert_timestamp(cls, v: str | datetime) -> datetime:
        """Convert ISO 8601 string or timestamp to datetime.

        Args:
            v: ISO 8601 datetime string or datetime object

        Returns:
            datetime object
        """
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return datetime.fromtimestamp(v / 1000)


class CandleWeek(BaseModel):
    """Week candle (주봉) data.

    OHLCV data for weekly candles (Monday 00:00 UTC based).
    """

    model_config = ConfigDict(strict=True)

    market: str = Field(..., description="마켓 코드")
    candle_date_time_utc: datetime = Field(..., description="캔들 기준 시각 (월요일 0시 UTC)")
    candle_date_time_kst: datetime = Field(..., description="캔들 기준 시각 (월요일 9시 KST)")
    opening_price: Decimal = Field(..., description="시가")
    high_price: Decimal = Field(..., description="고가")
    low_price: Decimal = Field(..., description="저가")
    trade_price: Decimal = Field(..., description="종가")
    timestamp: datetime = Field(..., description="마지막 틱 타임스탬프")
    candle_acc_trade_price: Decimal = Field(..., description="누적 거래 금액")
    candle_acc_trade_volume: Decimal = Field(..., description="누적 거래량")
    first_day_of_period: str = Field(..., description="캔들 기간의 첫 날 (YYYY-MM-DD)")

    @field_validator(
        "opening_price",
        "high_price",
        "low_price",
        "trade_price",
        "candle_acc_trade_price",
        "candle_acc_trade_volume",
        mode="before",
    )
    @classmethod
    def parse_decimal(cls, v: str | float | Decimal | int) -> Decimal:
        """Parse string/float values to Decimal for financial precision."""
        if isinstance(v, (str, int)):
            return Decimal(str(v))
        if isinstance(v, float):
            return Decimal(str(v))
        return v

    @field_validator("candle_date_time_utc", "candle_date_time_kst", "timestamp", mode="before")
    @classmethod
    def convert_timestamp(cls, v: str | datetime) -> datetime:
        """Convert ISO 8601 string or timestamp to datetime.

        Args:
            v: ISO 8601 datetime string or datetime object

        Returns:
            datetime object
        """
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return datetime.fromtimestamp(v / 1000)


class CandleMonth(BaseModel):
    """Month candle (월봉) data.

    OHLCV data for monthly candles (1st day 00:00 UTC based).
    """

    model_config = ConfigDict(strict=True)

    market: str = Field(..., description="마켓 코드")
    candle_date_time_utc: datetime = Field(..., description="캔들 기준 시각 (1일 0시 UTC)")
    candle_date_time_kst: datetime = Field(..., description="캔들 기준 시각 (1일 9시 KST)")
    opening_price: Decimal = Field(..., description="시가")
    high_price: Decimal = Field(..., description="고가")
    low_price: Decimal = Field(..., description="저가")
    trade_price: Decimal = Field(..., description="종가")
    timestamp: datetime = Field(..., description="마지막 틱 타임스탬프")
    candle_acc_trade_price: Decimal = Field(..., description="누적 거래 금액")
    candle_acc_trade_volume: Decimal = Field(..., description="누적 거래량")
    first_day_of_period: str = Field(..., description="캔들 기간의 첫 날 (YYYY-MM-DD)")

    @field_validator(
        "opening_price",
        "high_price",
        "low_price",
        "trade_price",
        "candle_acc_trade_price",
        "candle_acc_trade_volume",
        mode="before",
    )
    @classmethod
    def parse_decimal(cls, v: str | float | Decimal | int) -> Decimal:
        """Parse string/float values to Decimal for financial precision."""
        if isinstance(v, (str, int)):
            return Decimal(str(v))
        if isinstance(v, float):
            return Decimal(str(v))
        return v

    @field_validator("candle_date_time_utc", "candle_date_time_kst", "timestamp", mode="before")
    @classmethod
    def convert_timestamp(cls, v: str | datetime) -> datetime:
        """Convert ISO 8601 string or timestamp to datetime.

        Args:
            v: ISO 8601 datetime string or datetime object

        Returns:
            datetime object
        """
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return datetime.fromtimestamp(v / 1000)


class Orderbook(BaseModel):
    """Orderbook (호가) information.

    Current orderbook state with ask/bid prices and volumes.
    """

    model_config = ConfigDict(strict=True)

    market: str = Field(..., description="마켓 코드")
    timestamp: datetime = Field(..., description="호가 타임스탬프")
    total_ask_size: Decimal = Field(..., description="총 매도 잔량")
    total_bid_size: Decimal = Field(..., description="총 매수 잔량")
    orderbook_units: list[OrderbookUnit] = Field(..., description="호가 리스트 (최대 15개)")

    @field_validator("total_ask_size", "total_bid_size", mode="before")
    @classmethod
    def parse_decimal(cls, v: str | float | Decimal | int) -> Decimal:
        """Parse string/float values to Decimal for financial precision."""
        if isinstance(v, (str, int)):
            return Decimal(str(v))
        if isinstance(v, float):
            return Decimal(str(v))
        return v

    @field_validator("timestamp", mode="before")
    @classmethod
    def convert_timestamp(cls, v: int | datetime) -> datetime:
        """Convert Unix timestamp (milliseconds) to datetime.

        Args:
            v: Unix timestamp in milliseconds or datetime object

        Returns:
            datetime object
        """
        if isinstance(v, datetime):
            return v
        return datetime.fromtimestamp(v / 1000)


class Trade(BaseModel):
    """Trade (체결) information.

    Individual trade execution data.
    """

    model_config = ConfigDict(strict=True)

    market: str = Field(..., description="마켓 코드")
    trade_date_utc: str = Field(..., description="체결 일자 UTC (YYYY-MM-DD)")
    trade_time_utc: str = Field(..., description="체결 시각 UTC (HH:MM:SS)")
    timestamp: datetime = Field(..., description="체결 타임스탬프")
    trade_price: Decimal = Field(..., description="체결 가격")
    trade_volume: Decimal = Field(..., description="체결량")
    prev_closing_price: Decimal = Field(..., description="전일 종가")
    change_price: Decimal = Field(..., description="변화액")
    ask_bid: AskBid = Field(..., description="매수/매도 구분")
    sequential_id: int = Field(..., description="체결 번호 (순차적으로 증가)")

    @field_validator("ask_bid", mode="before")
    @classmethod
    def parse_ask_bid(cls, v: str | AskBid) -> AskBid:
        """Parse string to AskBid enum."""
        if isinstance(v, str):
            return AskBid(v)
        return v

    @field_validator(
        "trade_price", "trade_volume", "prev_closing_price", "change_price", mode="before"
    )
    @classmethod
    def parse_decimal(cls, v: str | float | Decimal | int) -> Decimal:
        """Parse string/float values to Decimal for financial precision."""
        if isinstance(v, (str, int)):
            return Decimal(str(v))
        if isinstance(v, float):
            return Decimal(str(v))
        return v

    @field_validator("timestamp", mode="before")
    @classmethod
    def convert_timestamp(cls, v: int | datetime) -> datetime:
        """Convert Unix timestamp (milliseconds) to datetime.

        Args:
            v: Unix timestamp in milliseconds or datetime object

        Returns:
            datetime object
        """
        if isinstance(v, datetime):
            return v
        return datetime.fromtimestamp(v / 1000)
