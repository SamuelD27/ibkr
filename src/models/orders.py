"""Order models for IBKR Trading Bot."""
from dataclasses import dataclass
from enum import Enum


class Action(Enum):
    """Strategy decision actions."""
    HOLD = "hold"
    BUY = "buy"
    EXIT = "exit"


@dataclass
class Order:
    """Order to be submitted to execution engine."""
    strategy_name: str
    symbol: str
    action: str           # "BUY" or "SELL"
    quantity: int
    order_type: str       # "MARKET", "LIMIT"
    limit_price: float | None = None


@dataclass
class OrderResult:
    """Result of order submission."""
    order_id: int
    status: str           # "submitted", "filled", "rejected", "cancelled"
    fill_price: float | None = None
    fill_quantity: int | None = None
    message: str | None = None
