"""Tests for IBKR Collector."""
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from datetime import datetime
import pytest


@pytest.fixture
def mock_connection():
    """Create a mock IBKR connection."""
    from src.collectors.ibkr.connection import IBKRConnection

    conn = Mock(spec=IBKRConnection)
    conn.is_connected.return_value = True
    conn.ib = Mock()
    return conn


@pytest.fixture
def mock_event_bus():
    """Create a mock event bus."""
    from src.core.event_bus import EventBus

    bus = Mock(spec=EventBus)
    return bus


@pytest.fixture
def mock_data_store():
    """Create a mock data store."""
    from src.core.data_store import DataStore

    store = Mock(spec=DataStore)
    return store


def test_collector_init(mock_connection, mock_event_bus, mock_data_store):
    from src.collectors.ibkr.collector import IBKRCollector

    collector = IBKRCollector(
        connection=mock_connection,
        event_bus=mock_event_bus,
        data_store=mock_data_store,
        market_symbol="SPY",
        scan_interval_hours=24.0,
    )

    assert collector.connection is mock_connection
    assert collector.event_bus is mock_event_bus
    assert collector.data_store is mock_data_store
    assert collector.market_symbol == "SPY"
    assert collector.scan_interval_hours == 24.0


def test_collector_is_running(mock_connection, mock_event_bus, mock_data_store):
    from src.collectors.ibkr.collector import IBKRCollector

    collector = IBKRCollector(
        connection=mock_connection,
        event_bus=mock_event_bus,
        data_store=mock_data_store,
    )

    assert not collector.is_running


def test_collector_stop(mock_connection, mock_event_bus, mock_data_store):
    from src.collectors.ibkr.collector import IBKRCollector

    collector = IBKRCollector(
        connection=mock_connection,
        event_bus=mock_event_bus,
        data_store=mock_data_store,
    )

    collector._running = True
    collector.stop()

    assert not collector.is_running


def test_collector_publish_price_bars(mock_connection, mock_event_bus, mock_data_store):
    from src.collectors.ibkr.collector import IBKRCollector
    from src.models import PriceBar

    collector = IBKRCollector(
        connection=mock_connection,
        event_bus=mock_event_bus,
        data_store=mock_data_store,
    )

    bars = [
        PriceBar(
            symbol="AAPL",
            date=datetime(2026, 1, 5),
            open=150.0,
            high=152.0,
            low=149.0,
            close=151.0,
            volume=1000000,
        )
    ]

    collector._publish_price_bars("AAPL", bars)

    mock_event_bus.publish.assert_called_once()
    event = mock_event_bus.publish.call_args[0][0]
    assert event.type == "price_bar"
    assert event.symbol == "AAPL"
    assert event.source == "ibkr"


def test_collector_publish_market_bars(mock_connection, mock_event_bus, mock_data_store):
    from src.collectors.ibkr.collector import IBKRCollector
    from src.models import PriceBar

    collector = IBKRCollector(
        connection=mock_connection,
        event_bus=mock_event_bus,
        data_store=mock_data_store,
    )

    bars = [
        PriceBar(
            symbol="SPY",
            date=datetime(2026, 1, 5),
            open=500.0,
            high=505.0,
            low=498.0,
            close=503.0,
            volume=50000000,
        )
    ]

    collector._publish_market_bars(bars)

    mock_event_bus.publish.assert_called_once()
    event = mock_event_bus.publish.call_args[0][0]
    assert event.type == "market_bar"
    assert event.symbol == "SPY"
    assert event.source == "ibkr"


def test_collector_publish_fundamental_data(mock_connection, mock_event_bus, mock_data_store):
    from src.collectors.ibkr.collector import IBKRCollector

    collector = IBKRCollector(
        connection=mock_connection,
        event_bus=mock_event_bus,
        data_store=mock_data_store,
    )

    details = {
        "company_name": "Apple Inc",
        "industry": "Technology",
        "category": "Consumer Electronics",
        "subcategory": "Smartphones",
    }

    collector._publish_fundamental_data("AAPL", details)

    mock_event_bus.publish.assert_called_once()
    event = mock_event_bus.publish.call_args[0][0]
    assert event.type == "fundamental_data"
    assert event.symbol == "AAPL"
    assert event.source == "ibkr"
    assert event.payload["company_name"] == "Apple Inc"
    assert event.payload["industry"] == "Technology"


@pytest.mark.asyncio
async def test_collector_rate_limit(mock_connection, mock_event_bus, mock_data_store):
    from src.collectors.ibkr.collector import IBKRCollector
    import time

    collector = IBKRCollector(
        connection=mock_connection,
        event_bus=mock_event_bus,
        data_store=mock_data_store,
    )

    # First request should not wait
    start = time.time()
    await collector._rate_limit()
    first_elapsed = time.time() - start

    # Second request should wait (at least partially)
    start = time.time()
    await collector._rate_limit()
    second_elapsed = time.time() - start

    # First request should be fast
    assert first_elapsed < 0.02

    # Second request should have some delay (0.05s interval)
    # Allow some tolerance for timing
    assert second_elapsed >= 0.03 or first_elapsed + second_elapsed >= 0.05
