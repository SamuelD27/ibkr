"""Market data models for IBKR Trading Bot."""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any


@dataclass
class PriceBar:
    """OHLCV price bar data."""
    symbol: str
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        d = asdict(self)
        d["date"] = self.date.isoformat()
        return d


@dataclass
class ContractInfo:
    """Contract details from IBKR."""
    symbol: str
    con_id: int
    long_name: str
    industry: str
    category: str
    subcategory: str
    exchange: str
    currency: str
