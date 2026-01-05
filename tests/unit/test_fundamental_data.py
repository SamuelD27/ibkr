"""Tests for FundamentalData model."""
from datetime import datetime
import pytest


def test_fundamental_data_creation():
    from src.models.fundamental_data import FundamentalData

    data = FundamentalData(
        symbol="AAPL",
        timestamp=datetime(2026, 1, 5),
        company_name="Apple Inc",
        cik="0000320193",
        employees=166000,
        shares_outstanding=14776353000.0,
        float_shares=14525947723.0,
        industry="Technology",
        category="Computers",
        subcategory="Consumer Electronics",
        raw_xml="<test/>"
    )

    assert data.symbol == "AAPL"
    assert data.company_name == "Apple Inc"
    assert data.employees == 166000


def test_fundamental_data_with_none_fields():
    from src.models.fundamental_data import FundamentalData

    data = FundamentalData(
        symbol="NEWCO",
        timestamp=datetime(2026, 1, 5),
        company_name="New Company Inc",
        cik="0001234567",
        employees=None,
        shares_outstanding=None,
        float_shares=None,
        industry=None,
        category=None,
        subcategory=None,
        raw_xml="<incomplete/>"
    )

    assert data.employees is None
    assert data.shares_outstanding is None
