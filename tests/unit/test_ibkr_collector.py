"""Tests for IBKR Collector."""
from unittest.mock import Mock, MagicMock, AsyncMock
from datetime import datetime
import pytest


@pytest.fixture
def mock_connection():
    """Create a mock IBKR connection."""
    from src.collectors.ibkr.connection import IBKRConnection

    conn = Mock(spec=IBKRConnection)
    conn.is_connected.return_value = True
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

    watchlist = ["AAPL", "MSFT", "GOOGL"]

    collector = IBKRCollector(
        connection=mock_connection,
        event_bus=mock_event_bus,
        data_store=mock_data_store,
        watchlist=watchlist,
    )

    assert collector.connection is mock_connection
    assert collector.event_bus is mock_event_bus
    assert collector.data_store is mock_data_store
    assert collector.watchlist == watchlist


def test_collector_is_running(mock_connection, mock_event_bus, mock_data_store):
    from src.collectors.ibkr.collector import IBKRCollector

    collector = IBKRCollector(
        connection=mock_connection,
        event_bus=mock_event_bus,
        data_store=mock_data_store,
        watchlist=["AAPL"],
    )

    assert not collector.is_running


def test_collector_stop(mock_connection, mock_event_bus, mock_data_store):
    from src.collectors.ibkr.collector import IBKRCollector

    collector = IBKRCollector(
        connection=mock_connection,
        event_bus=mock_event_bus,
        data_store=mock_data_store,
        watchlist=["AAPL"],
    )

    collector._running = True
    collector.stop()

    assert not collector.is_running


def test_on_price_bar_publishes_event(mock_connection, mock_event_bus, mock_data_store):
    from src.collectors.ibkr.collector import IBKRCollector
    from src.models import PriceBar

    collector = IBKRCollector(
        connection=mock_connection,
        event_bus=mock_event_bus,
        data_store=mock_data_store,
        watchlist=["AAPL"],
    )

    bar = PriceBar(
        symbol="AAPL",
        date=datetime(2026, 1, 5),
        open=150.0,
        high=152.0,
        low=149.0,
        close=151.0,
        volume=1000000,
    )

    collector._on_price_bar(bar)

    mock_event_bus.publish.assert_called_once()
    event = mock_event_bus.publish.call_args[0][0]
    assert event.type == "price_bar"
    assert event.symbol == "AAPL"
    assert event.source == "ibkr"


def test_on_price_bar_writes_to_store(mock_connection, mock_event_bus, mock_data_store):
    from src.collectors.ibkr.collector import IBKRCollector
    from src.models import PriceBar

    collector = IBKRCollector(
        connection=mock_connection,
        event_bus=mock_event_bus,
        data_store=mock_data_store,
        watchlist=["AAPL"],
    )

    bar = PriceBar(
        symbol="AAPL",
        date=datetime(2026, 1, 5),
        open=150.0,
        high=152.0,
        low=149.0,
        close=151.0,
        volume=1000000,
    )

    collector._on_price_bar(bar)

    mock_data_store.write_bars.assert_called_once_with("AAPL", [bar])


def test_on_fundamental_data_publishes_event(mock_connection, mock_event_bus, mock_data_store):
    from src.collectors.ibkr.collector import IBKRCollector
    from src.models import FundamentalData

    collector = IBKRCollector(
        connection=mock_connection,
        event_bus=mock_event_bus,
        data_store=mock_data_store,
        watchlist=["AAPL"],
    )

    data = FundamentalData(
        symbol="AAPL",
        timestamp=datetime.now(),
        company_name="Apple Inc",
        cik="0000320193",
        employees=166000,
        shares_outstanding=14776353000.0,
        float_shares=14525947723.0,
        industry="Technology",
        category=None,
        subcategory=None,
        raw_xml="<test/>",
    )

    collector._on_fundamental_data(data)

    mock_event_bus.publish.assert_called_once()
    event = mock_event_bus.publish.call_args[0][0]
    assert event.type == "fundamental_data"
    assert event.symbol == "AAPL"


def test_on_fundamental_data_writes_to_store(mock_connection, mock_event_bus, mock_data_store):
    from src.collectors.ibkr.collector import IBKRCollector
    from src.models import FundamentalData

    collector = IBKRCollector(
        connection=mock_connection,
        event_bus=mock_event_bus,
        data_store=mock_data_store,
        watchlist=["AAPL"],
    )

    data = FundamentalData(
        symbol="AAPL",
        timestamp=datetime.now(),
        company_name="Apple Inc",
        cik="0000320193",
        employees=166000,
        shares_outstanding=14776353000.0,
        float_shares=14525947723.0,
        industry="Technology",
        category=None,
        subcategory=None,
        raw_xml="<test/>",
    )

    collector._on_fundamental_data(data)

    mock_data_store.write_fundamental.assert_called_once_with("AAPL", data)


def test_add_to_watchlist(mock_connection, mock_event_bus, mock_data_store):
    from src.collectors.ibkr.collector import IBKRCollector

    collector = IBKRCollector(
        connection=mock_connection,
        event_bus=mock_event_bus,
        data_store=mock_data_store,
        watchlist=["AAPL"],
    )

    collector.add_symbol("MSFT")

    assert "MSFT" in collector.watchlist


def test_remove_from_watchlist(mock_connection, mock_event_bus, mock_data_store):
    from src.collectors.ibkr.collector import IBKRCollector

    collector = IBKRCollector(
        connection=mock_connection,
        event_bus=mock_event_bus,
        data_store=mock_data_store,
        watchlist=["AAPL", "MSFT"],
    )

    collector.remove_symbol("MSFT")

    assert "MSFT" not in collector.watchlist
    assert "AAPL" in collector.watchlist
