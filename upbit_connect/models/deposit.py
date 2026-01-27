"""Deposit API models for Upbit.

This module contains Pydantic V2 models for Deposit API endpoints including:
- Deposit: Individual deposit information
- DepositAddress: Deposit address information
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Deposit(BaseModel):
    """Deposit information (입금 정보).

    Represents a single deposit and its state.
    """

    model_config = ConfigDict(strict=True)

    type: str = Field(..., description="Deposit type")
    uuid: str = Field(..., description="Deposit UUID")
    currency: str = Field(..., description="Currency code")
    net_type: str = Field(..., description="Network type")
    txid: str | None = Field(None, description="Transaction ID")
    state: str = Field(..., description="Deposit state")
    created_at: datetime = Field(..., description="Deposit creation time")
    done_at: datetime | None = Field(None, description="Deposit completion time")
    amount: Decimal = Field(..., description="Deposit amount")
    fee: Decimal = Field(..., description="Deposit fee")
    transaction_type: str = Field(..., description="Transaction type")

    @field_validator("amount", "fee", mode="before")
    @classmethod
    def parse_decimal(cls, v: str | float | Decimal | None) -> Decimal | None:
        """Parse string/float values to Decimal for financial precision."""
        if v is None:
            return None
        if isinstance(v, (str, int, float)):
            return Decimal(str(v))
        return v

    @field_validator("created_at", "done_at", mode="before")
    @classmethod
    def parse_datetime(cls, v: str | datetime | None) -> datetime | None:
        """Parse ISO 8601 string to datetime."""
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        return datetime.fromisoformat(v.replace("Z", "+00:00"))


class DepositAddress(BaseModel):
    """Deposit address information (입금 주소 정보).

    Contains the address and secondary address (memo/tag) for a currency.
    """

    model_config = ConfigDict(strict=True)

    currency: str = Field(..., description="Currency code")
    net_type: str = Field(..., description="Network type")
    deposit_address: str | None = Field(None, description="Deposit address")
    secondary_address: str | None = Field(
        None, description="Secondary address (e.g., Destination Tag, Memo)"
    )
