"""Withdrawal API models for Upbit.

This module contains Pydantic V2 models for Withdrawal API endpoints including:
- Withdrawal: Individual withdrawal information
- WithdrawalChance: Withdrawal possibility and limit information
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Withdrawal(BaseModel):
    """Withdrawal information (출금 정보).

    Represents a single withdrawal request and its state.
    """

    model_config = ConfigDict(strict=True)

    type: str = Field(..., description="Withdrawal type")
    uuid: str = Field(..., description="Withdrawal UUID")
    currency: str = Field(..., description="Currency code")
    net_type: str = Field(..., description="Network type")
    txid: str | None = Field(None, description="Transaction ID")
    state: str = Field(..., description="Withdrawal state")
    created_at: datetime = Field(..., description="Withdrawal creation time")
    done_at: datetime | None = Field(None, description="Withdrawal completion time")
    amount: Decimal = Field(..., description="Withdrawal amount")
    fee: Decimal = Field(..., description="Withdrawal fee")
    transaction_type: str = Field(..., description="Transaction type")
    is_cancelable: bool = Field(False, description="Whether the withdrawal can be canceled")

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


class MemberLevel(BaseModel):
    """User's membership level information."""

    model_config = ConfigDict(strict=True)

    security_level: int = Field(..., description="Security level")
    fee_level: int = Field(..., description="Fee level")
    email_verified: bool = Field(..., description="Whether email is verified")
    identity_verified: bool = Field(..., description="Whether identity is verified")
    bank_account_verified: bool = Field(..., description="Whether bank account is verified")
    kakao_pay_auth_verified: bool = Field(..., description="Whether KakaoPay auth is verified")
    second_auth_verified: bool = Field(..., description="Whether second auth is verified")
    deposit_user_level: int = Field(..., description="Deposit user level")


class WithdrawalCurrency(BaseModel):
    """Currency information for withdrawal."""

    model_config = ConfigDict(strict=True)

    code: str = Field(..., description="Currency code")
    withdraw_fee: Decimal = Field(..., description="Withdrawal fee")
    is_coin: bool = Field(..., description="Whether it's a digital asset")
    wallet_state: str = Field(..., description="Wallet state")
    wallet_support: list[str] = Field(..., description="Supported wallet operations")

    @field_validator("withdraw_fee", mode="before")
    @classmethod
    def parse_decimal(cls, v: str | float | Decimal) -> Decimal:
        """Parse string/float values to Decimal for financial precision."""
        if isinstance(v, (str, int, float)):
            return Decimal(str(v))
        return v


class WithdrawalAccount(BaseModel):
    """Account information for withdrawal."""

    model_config = ConfigDict(strict=True)

    currency: str = Field(..., description="Currency code")
    balance: Decimal = Field(..., description="Total available balance")
    locked: Decimal = Field(..., description="Balance locked in orders/withdrawals")
    avg_buy_price: Decimal = Field(..., description="Average buy price")
    avg_buy_price_modified: bool = Field(..., description="Whether average buy price was modified")
    unit_currency: str = Field(..., description="Unit currency")

    @field_validator("balance", "locked", "avg_buy_price", mode="before")
    @classmethod
    def parse_decimal(cls, v: str | float | Decimal) -> Decimal:
        """Parse string/float values to Decimal for financial precision."""
        if isinstance(v, (str, int, float)):
            return Decimal(str(v))
        return v


class WithdrawalLimit(BaseModel):
    """Withdrawal limit information."""

    model_config = ConfigDict(strict=True)

    currency: str = Field(..., description="Currency code")
    minimum: Decimal | None = Field(None, description="Minimum withdrawal amount")
    fixed: int | None = Field(None, description="Number of decimal places")
    can_withdraw: bool = Field(..., description="Whether withdrawal is currently possible")
    maximum: Decimal | None = Field(None, description="Maximum withdrawal amount")
    onetime: Decimal | None = Field(None, description="One-time withdrawal limit")
    daily: Decimal | None = Field(None, description="Daily withdrawal limit")
    remain_onetime: Decimal | None = Field(None, description="Remaining one-time withdrawal limit")
    remain_daily: Decimal | None = Field(None, description="Remaining daily withdrawal limit")

    @field_validator(
        "minimum", "maximum", "onetime", "daily", "remain_onetime", "remain_daily", mode="before"
    )
    @classmethod
    def parse_decimal(cls, v: str | float | Decimal | None) -> Decimal | None:
        """Parse string/float values to Decimal for financial precision."""
        if v is None:
            return None
        if isinstance(v, (str, int, float)):
            return Decimal(str(v))
        return v


class WithdrawalChance(BaseModel):
    """Withdrawal chance information (출금 가능 정보).

    Contains details about user's limits, account balance, and currency rules.
    """

    model_config = ConfigDict(strict=True)

    member_level: MemberLevel = Field(..., description="Member level info")
    currency: WithdrawalCurrency = Field(..., description="Currency info")
    account: WithdrawalAccount = Field(..., description="Account info")
    withdrawal_limit: WithdrawalLimit = Field(..., description="Withdrawal limit info")
