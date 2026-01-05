"""Fundamental data model for IBKR Trading Bot."""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class FundamentalData:
    """Parsed fundamental data from IBKR XML."""
    symbol: str
    timestamp: datetime

    # Company info
    company_name: str
    cik: str
    employees: int | None

    # Share data
    shares_outstanding: float | None
    float_shares: float | None

    # Classification
    industry: str | None
    category: str | None
    subcategory: str | None

    # Raw data preserved for debugging
    raw_xml: str
