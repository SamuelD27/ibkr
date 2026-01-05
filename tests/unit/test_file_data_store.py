"""Tests for FileDataStore implementation."""
from datetime import datetime
import tempfile
import pytest


@pytest.fixture
def temp_store():
    """Create a FileDataStore with a temporary directory."""
    from src.core.data_store import FileDataStore

    with tempfile.TemporaryDirectory() as tmpdir:
        yield FileDataStore(base_path=tmpdir)


# =============================================================================
# Price Bar Tests
# =============================================================================

def test_write_and_read_bars(temp_store):
    from src.models import PriceBar

    bars = [
        PriceBar(symbol="AAPL", date=datetime(2026, 1, 5), open=150.0, high=152.0, low=149.0, close=151.0, volume=1000000),
        PriceBar(symbol="AAPL", date=datetime(2026, 1, 6), open=151.0, high=153.0, low=150.0, close=152.0, volume=1100000),
    ]

    temp_store.write_bars("AAPL", bars)

    result = temp_store.read_bars("AAPL", datetime(2026, 1, 1), datetime(2026, 1, 31))

    assert len(result) == 2
    assert result[0].symbol == "AAPL"
    assert result[0].close == 151.0
    assert result[1].close == 152.0


def test_read_bars_with_date_filter(temp_store):
    from src.models import PriceBar

    bars = [
        PriceBar(symbol="AAPL", date=datetime(2026, 1, 5), open=150.0, high=152.0, low=149.0, close=151.0, volume=1000000),
        PriceBar(symbol="AAPL", date=datetime(2026, 1, 10), open=151.0, high=153.0, low=150.0, close=152.0, volume=1100000),
        PriceBar(symbol="AAPL", date=datetime(2026, 1, 15), open=152.0, high=154.0, low=151.0, close=153.0, volume=1200000),
    ]

    temp_store.write_bars("AAPL", bars)

    result = temp_store.read_bars("AAPL", datetime(2026, 1, 8), datetime(2026, 1, 12))

    assert len(result) == 1
    assert result[0].date == datetime(2026, 1, 10)


def test_read_bars_empty_for_missing_symbol(temp_store):
    result = temp_store.read_bars("MISSING", datetime(2026, 1, 1), datetime(2026, 1, 31))
    assert result == []


def test_write_bars_appends_to_existing(temp_store):
    from src.models import PriceBar

    bars1 = [
        PriceBar(symbol="AAPL", date=datetime(2026, 1, 5), open=150.0, high=152.0, low=149.0, close=151.0, volume=1000000),
    ]
    bars2 = [
        PriceBar(symbol="AAPL", date=datetime(2026, 1, 6), open=151.0, high=153.0, low=150.0, close=152.0, volume=1100000),
    ]

    temp_store.write_bars("AAPL", bars1)
    temp_store.write_bars("AAPL", bars2)

    result = temp_store.read_bars("AAPL", datetime(2026, 1, 1), datetime(2026, 1, 31))

    assert len(result) == 2


def test_write_bars_updates_existing_date(temp_store):
    from src.models import PriceBar

    bars1 = [
        PriceBar(symbol="AAPL", date=datetime(2026, 1, 5), open=150.0, high=152.0, low=149.0, close=151.0, volume=1000000),
    ]
    bars2 = [
        PriceBar(symbol="AAPL", date=datetime(2026, 1, 5), open=150.0, high=152.0, low=149.0, close=155.0, volume=1000000),
    ]

    temp_store.write_bars("AAPL", bars1)
    temp_store.write_bars("AAPL", bars2)

    result = temp_store.read_bars("AAPL", datetime(2026, 1, 1), datetime(2026, 1, 31))

    assert len(result) == 1
    assert result[0].close == 155.0  # Updated value


def test_write_empty_bars_does_nothing(temp_store):
    temp_store.write_bars("AAPL", [])
    result = temp_store.read_bars("AAPL", datetime(2026, 1, 1), datetime(2026, 1, 31))
    assert result == []
