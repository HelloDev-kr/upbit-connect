"""WebSocket API response models for Upbit.

This module defines Pydantic V2 models for Upbit WebSocket API responses.
WebSocket responses have different field names and structures compared to REST API:
- Uses 'code' instead of 'market'
- Includes 'type' and 'stream_type' fields
- Some fields present in REST are absent in WebSocket and vice versa

Models:
- WsTicker: Real-time ticker (현재가) data
- WsOrderbook: Real-time orderbook (호가) data
- WsTrade: Real-time trade (체결) data

All price and volume fields use Decimal for precision.
All timestamp fields are converted to datetime objects.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StreamType(str, Enum):
    """WebSocket stream type."""

    SNAPSHOT = "SNAPSHOT"
    REALTIME = "REALTIME"


class AskBid(str, Enum):
    """Trade ask/bid type."""

    ASK = "ASK"
    BID = "BID"


class ChangeType(str, Enum):
    """Price change type."""

    EVEN = "EVEN"
    RISE = "RISE"
    FALL = "FALL"


class MarketState(str, Enum):
    """Market trading state."""

    PREVIEW = "PREVIEW"
    ACTIVE = "ACTIVE"
    DELISTED = "DELISTED"


class MarketWarning(str, Enum):
    """Market warning type."""

    NONE = "NONE"
    CAUTION = "CAUTION"


class WsOrderbookUnit(BaseModel):
    """Single orderbook unit for WebSocket (호가 단위).

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
        if isinstance(v, Decimal):
            return v
        return Decimal(str(v))


class WsTicker(BaseModel):
    """WebSocket Ticker (현재가) information.

    Real-time market data for a trading pair including price, volume, and change statistics.
    Note: Field names differ from REST API (e.g., 'code' instead of 'market').
    """

    model_config = ConfigDict(strict=True)

    type: str = Field(..., description="메시지 타입 (ticker)")
    code: str = Field(..., description="마켓 코드 (e.g., KRW-BTC)")
    opening_price: Decimal = Field(..., description="시가")
    high_price: Decimal = Field(..., description="고가")
    low_price: Decimal = Field(..., description="저가")
    trade_price: Decimal = Field(..., description="현재가")
    prev_closing_price: Decimal = Field(..., description="전일 종가")
    change: ChangeType = Field(..., description="전일 대비 (EVEN/RISE/FALL)")
    change_price: Decimal = Field(..., description="전일 대비 가격 변화량")
    signed_change_price: Decimal = Field(..., description="부호가 있는 변화액")
    change_rate: Decimal = Field(..., description="전일 대비 변화율")
    signed_change_rate: Decimal = Field(..., description="부호가 있는 변화율")
    ask_bid: AskBid = Field(..., description="최근 거래 매수/매도 구분")
    trade_volume: Decimal = Field(..., description="가장 최근 거래량")
    acc_trade_volume: Decimal = Field(..., description="누적 거래량 (UTC 0시 기준)")
    acc_trade_volume_24h: Decimal = Field(..., description="24시간 누적 거래량")
    acc_trade_price: Decimal = Field(..., description="누적 거래대금 (UTC 0시 기준)")
    acc_trade_price_24h: Decimal = Field(..., description="24시간 누적 거래대금")
    acc_ask_volume: Decimal = Field(..., description="누적 매도량")
    acc_bid_volume: Decimal = Field(..., description="누적 매수량")
    trade_date: str = Field(..., description="최근 거래 일자 (YYYYMMDD)")
    trade_time: str = Field(..., description="최근 거래 시각 (HHMMSS)")
    trade_timestamp: datetime = Field(..., description="최근 거래 타임스탬프")
    highest_52_week_price: Decimal = Field(..., description="52주 최고가")
    highest_52_week_date: str = Field(..., description="52주 최고가 달성일 (YYYY-MM-DD)")
    lowest_52_week_price: Decimal = Field(..., description="52주 최저가")
    lowest_52_week_date: str = Field(..., description="52주 최저가 달성일 (YYYY-MM-DD)")
    market_state: MarketState = Field(..., description="거래 상태")
    is_trading_suspended: bool = Field(..., description="거래 정지 여부")
    delisting_date: str | None = Field(None, description="상장 폐지 일자")
    market_warning: MarketWarning = Field(..., description="유의 종목 여부")
    timestamp: datetime = Field(..., description="타임스탬프")
    stream_type: StreamType = Field(..., description="스트림 타입 (SNAPSHOT/REALTIME)")

    @field_validator("change", mode="before")
    @classmethod
    def parse_change_type(cls, v: str | ChangeType) -> ChangeType:
        """Parse string to ChangeType enum."""
        if isinstance(v, str):
            return ChangeType(v)
        return v

    @field_validator("ask_bid", mode="before")
    @classmethod
    def parse_ask_bid(cls, v: str | AskBid) -> AskBid:
        """Parse string to AskBid enum."""
        if isinstance(v, str):
            return AskBid(v)
        return v

    @field_validator("market_state", mode="before")
    @classmethod
    def parse_market_state(cls, v: str | MarketState) -> MarketState:
        """Parse string to MarketState enum."""
        if isinstance(v, str):
            return MarketState(v)
        return v

    @field_validator("market_warning", mode="before")
    @classmethod
    def parse_market_warning(cls, v: str | MarketWarning) -> MarketWarning:
        """Parse string to MarketWarning enum."""
        if isinstance(v, str):
            return MarketWarning(v)
        return v

    @field_validator("stream_type", mode="before")
    @classmethod
    def parse_stream_type(cls, v: str | StreamType) -> StreamType:
        """Parse string to StreamType enum."""
        if isinstance(v, str):
            return StreamType(v)
        return v

    @field_validator(
        "opening_price",
        "high_price",
        "low_price",
        "trade_price",
        "prev_closing_price",
        "change_price",
        "signed_change_price",
        "change_rate",
        "signed_change_rate",
        "trade_volume",
        "acc_trade_volume",
        "acc_trade_volume_24h",
        "acc_trade_price",
        "acc_trade_price_24h",
        "acc_ask_volume",
        "acc_bid_volume",
        "highest_52_week_price",
        "lowest_52_week_price",
        mode="before",
    )
    @classmethod
    def parse_decimal(cls, v: str | float | Decimal | int) -> Decimal:
        """Parse string/float values to Decimal for financial precision."""
        if isinstance(v, Decimal):
            return v
        return Decimal(str(v))

    @field_validator("trade_timestamp", "timestamp", mode="before")
    @classmethod
    def convert_timestamp(cls, v: int | datetime) -> datetime:
        """Convert Unix timestamp (milliseconds) to datetime."""
        if isinstance(v, datetime):
            return v
        return datetime.fromtimestamp(v / 1000)


class WsOrderbook(BaseModel):
    """WebSocket Orderbook (호가) information.

    Real-time orderbook state with ask/bid prices and volumes.
    Note: Field names differ from REST API (e.g., 'code' instead of 'market').
    """

    model_config = ConfigDict(strict=True)

    type: str = Field(..., description="메시지 타입 (orderbook)")
    code: str = Field(..., description="마켓 코드 (e.g., KRW-BTC)")
    timestamp: datetime = Field(..., description="호가 타임스탬프")
    total_ask_size: Decimal = Field(..., description="총 매도 잔량")
    total_bid_size: Decimal = Field(..., description="총 매수 잔량")
    orderbook_units: list[WsOrderbookUnit] = Field(..., description="호가 리스트")
    stream_type: StreamType = Field(..., description="스트림 타입 (SNAPSHOT/REALTIME)")
    level: int = Field(0, description="호가 레벨 (기본값 0)")

    @field_validator("stream_type", mode="before")
    @classmethod
    def parse_stream_type(cls, v: str | StreamType) -> StreamType:
        """Parse string to StreamType enum."""
        if isinstance(v, str):
            return StreamType(v)
        return v

    @field_validator("total_ask_size", "total_bid_size", mode="before")
    @classmethod
    def parse_decimal(cls, v: str | float | Decimal | int) -> Decimal:
        """Parse string/float values to Decimal for financial precision."""
        if isinstance(v, Decimal):
            return v
        return Decimal(str(v))

    @field_validator("timestamp", mode="before")
    @classmethod
    def convert_timestamp(cls, v: int | datetime) -> datetime:
        """Convert Unix timestamp (milliseconds) to datetime."""
        if isinstance(v, datetime):
            return v
        return datetime.fromtimestamp(v / 1000)


class WsTrade(BaseModel):
    """WebSocket Trade (체결) information.

    Real-time individual trade execution data.
    Note: Field names differ from REST API (e.g., 'code' instead of 'market').
    """

    model_config = ConfigDict(strict=True)

    type: str = Field(..., description="메시지 타입 (trade)")
    code: str = Field(..., description="마켓 코드 (e.g., KRW-BTC)")
    timestamp: datetime = Field(..., description="체결 타임스탬프")
    trade_date: str = Field(..., description="체결 일자 (YYYY-MM-DD)")
    trade_time: str = Field(..., description="체결 시각 (HH:MM:SS)")
    trade_timestamp: datetime = Field(..., description="체결 타임스탬프")
    trade_price: Decimal = Field(..., description="체결 가격")
    trade_volume: Decimal = Field(..., description="체결량")
    ask_bid: AskBid = Field(..., description="매수/매도 구분")
    prev_closing_price: Decimal = Field(..., description="전일 종가")
    change: ChangeType = Field(..., description="전일 대비 (EVEN/RISE/FALL)")
    change_price: Decimal = Field(..., description="변화액")
    sequential_id: int = Field(..., description="체결 번호 (순차적으로 증가)")
    best_ask_price: Decimal = Field(..., description="최우선 매도 호가")
    best_ask_size: Decimal = Field(..., description="최우선 매도 잔량")
    best_bid_price: Decimal = Field(..., description="최우선 매수 호가")
    best_bid_size: Decimal = Field(..., description="최우선 매수 잔량")
    stream_type: StreamType = Field(..., description="스트림 타입 (SNAPSHOT/REALTIME)")

    @field_validator("ask_bid", mode="before")
    @classmethod
    def parse_ask_bid(cls, v: str | AskBid) -> AskBid:
        """Parse string to AskBid enum."""
        if isinstance(v, str):
            return AskBid(v)
        return v

    @field_validator("change", mode="before")
    @classmethod
    def parse_change_type(cls, v: str | ChangeType) -> ChangeType:
        """Parse string to ChangeType enum."""
        if isinstance(v, str):
            return ChangeType(v)
        return v

    @field_validator("stream_type", mode="before")
    @classmethod
    def parse_stream_type(cls, v: str | StreamType) -> StreamType:
        """Parse string to StreamType enum."""
        if isinstance(v, str):
            return StreamType(v)
        return v

    @field_validator(
        "trade_price",
        "trade_volume",
        "prev_closing_price",
        "change_price",
        "best_ask_price",
        "best_ask_size",
        "best_bid_price",
        "best_bid_size",
        mode="before",
    )
    @classmethod
    def parse_decimal(cls, v: str | float | Decimal | int) -> Decimal:
        """Parse string/float values to Decimal for financial precision."""
        if isinstance(v, Decimal):
            return v
        return Decimal(str(v))

    @field_validator("timestamp", "trade_timestamp", mode="before")
    @classmethod
    def convert_timestamp(cls, v: int | datetime) -> datetime:
        """Convert Unix timestamp (milliseconds) to datetime."""
        if isinstance(v, datetime):
            return v
        return datetime.fromtimestamp(v / 1000)
