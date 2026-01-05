"""Tests for market data models."""
from datetime import datetime
import pytest


def test_price_bar_creation():
    from src.models.market_data import PriceBar

    bar = PriceBar(
        symbol="AAPL",
        date=datetime(2026, 1, 5),
        open=150.0,
        high=152.0,
        low=149.5,
        close=151.0,
        volume=1000000
    )

    assert bar.symbol == "AAPL"
    assert bar.open == 150.0
    assert bar.high == 152.0
    assert bar.low == 149.5
    assert bar.close == 151.0
    assert bar.volume == 1000000


def test_contract_info_creation():
    from src.models.market_data import ContractInfo

    info = ContractInfo(
        symbol="AAPL",
        con_id=265598,
        long_name="APPLE INC",
        industry="Technology",
        category="Computers",
        subcategory="Consumer Electronics",
        exchange="NASDAQ",
        currency="USD"
    )

    assert info.symbol == "AAPL"
    assert info.con_id == 265598
    assert info.long_name == "APPLE INC"


def test_price_bar_to_dict():
    from src.models.market_data import PriceBar

    bar = PriceBar(
        symbol="AAPL",
        date=datetime(2026, 1, 5),
        open=150.0,
        high=152.0,
        low=149.5,
        close=151.0,
        volume=1000000
    )

    d = bar.to_dict()
    assert d["symbol"] == "AAPL"
    assert d["close"] == 151.0
