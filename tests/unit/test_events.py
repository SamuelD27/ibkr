"""Tests for Event model."""
from datetime import datetime
import pytest


def test_event_creation():
    from src.models.events import Event

    event = Event(
        type="price_bar",
        symbol="AAPL",
        timestamp=datetime(2026, 1, 5, 10, 0, 0),
        ingested_at=datetime(2026, 1, 5, 10, 0, 1),
        source="ibkr",
        payload={"open": 150.0, "close": 151.0}
    )

    assert event.type == "price_bar"
    assert event.symbol == "AAPL"
    assert event.source == "ibkr"
    assert event.payload["open"] == 150.0


def test_event_with_none_symbol():
    from src.models.events import Event

    event = Event(
        type="system_start",
        symbol=None,
        timestamp=datetime(2026, 1, 5, 10, 0, 0),
        ingested_at=datetime(2026, 1, 5, 10, 0, 0),
        source="system",
        payload={}
    )

    assert event.symbol is None


def test_event_to_dict():
    from src.models.events import Event

    event = Event(
        type="price_bar",
        symbol="AAPL",
        timestamp=datetime(2026, 1, 5, 10, 0, 0),
        ingested_at=datetime(2026, 1, 5, 10, 0, 1),
        source="ibkr",
        payload={"open": 150.0}
    )

    d = event.to_dict()
    assert d["type"] == "price_bar"
    assert d["symbol"] == "AAPL"
    assert "timestamp" in d
