"""End-to-end integration tests for the full system."""
import asyncio
import tempfile
from datetime import datetime
import pytest
from ib_async import IB, Stock

from src.core.config import load_config, Config, IBKRConfig, DataStoreConfig, CollectorConfig, StrategyConfig
from src.core.orchestrator import Orchestrator
from src.core.event_bus import EventBus
from src.models import Event, PriceBar, FundamentalData
from src.strategies.example_value import ExampleValueStrategy


pytestmark = pytest.mark.asyncio


def create_test_config(tmpdir: str) -> Config:
    """Create a test configuration."""
    return Config(
        ibkr=IBKRConfig(host="127.0.0.1", port=7497, client_id=1),
        data_store=DataStoreConfig(backend="file", path=tmpdir),
        collector=CollectorConfig(watchlist=["AAPL", "MSFT"], fundamental_refresh_hours=24),
        strategies=[
            StrategyConfig(
                name="example_value",
                class_path="src.strategies.example_value.ExampleValueStrategy",
                allocated_capital=10000,
                enabled=True,
                params={"min_market_cap": 1_000_000_000},
            )
        ],
    )


def make_price_event(symbol: str, price: float, volume: int = 1000000) -> Event:
    """Create a price bar event."""
    now = datetime.now()
    return Event(
        type="price_bar",
        symbol=symbol,
        timestamp=now,
        ingested_at=now,
        source="test",
        payload={
            "symbol": symbol,
            "date": now.isoformat(),
            "open": price,
            "high": price + 1,
            "low": price - 1,
            "close": price,
            "volume": volume,
        },
    )


def make_fundamental_event(symbol: str, company_name: str, shares: float) -> Event:
    """Create a fundamental data event."""
    now = datetime.now()
    return Event(
        type="fundamental_data",
        symbol=symbol,
        timestamp=now,
        ingested_at=now,
        source="test",
        payload={
            "symbol": symbol,
            "company_name": company_name,
            "shares_outstanding": shares,
            "industry": "Technology",
        },
    )


async def test_orchestrator_initializes_with_config():
    """Test that orchestrator initializes correctly with config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = create_test_config(tmpdir)

        orchestrator = Orchestrator(config)

        assert orchestrator.event_bus is not None
        assert orchestrator.data_store is not None
        assert len(orchestrator.strategies) == 1
        assert orchestrator.strategies[0].name == "example_value"


async def test_strategy_receives_price_event():
    """Test that strategy receives and processes price events."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = create_test_config(tmpdir)
        orchestrator = Orchestrator(config)

        # Create and publish a price bar event
        event = make_price_event("AAPL", 185.5)
        orchestrator.event_bus.publish(event)

        # Verify strategy received the price
        strategy = orchestrator.strategies[0]
        assert "AAPL" in strategy._prices
        assert strategy._prices["AAPL"] == 185.5


async def test_strategy_receives_fundamental_event():
    """Test that strategy receives and processes fundamental data events."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = create_test_config(tmpdir)
        orchestrator = Orchestrator(config)

        # First send price to have current price
        orchestrator.event_bus.publish(make_price_event("AAPL", 185.5))

        # Now send fundamental data
        event = make_fundamental_event("AAPL", "Apple Inc", 15_000_000_000)
        orchestrator.event_bus.publish(event)

        # Verify strategy received the data
        strategy = orchestrator.strategies[0]
        assert "AAPL" in strategy._fundamentals
        assert strategy._fundamentals["AAPL"].company_name == "Apple Inc"


async def test_full_flow_with_live_data(ib_connection):
    """Test full flow: fetch real data -> publish events -> strategy processes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = create_test_config(tmpdir)
        orchestrator = Orchestrator(config)

        # Fetch real contract details
        contract = Stock("AAPL", "SMART", "USD")
        details = await ib_connection.reqContractDetailsAsync(contract)

        # Fetch real historical bars
        bars = await ib_connection.reqHistoricalDataAsync(
            contract,
            endDateTime="",
            durationStr="1 D",
            barSizeSetting="1 day",
            whatToShow="TRADES",
            useRTH=True,
        )

        # Create event from real data
        if bars:
            bar = bars[-1]  # Most recent bar
            event = make_price_event("AAPL", bar.close, int(bar.volume))
            orchestrator.event_bus.publish(event)

        # Verify strategy received real data
        strategy = orchestrator.strategies[0]
        assert "AAPL" in strategy._prices
        assert strategy._prices["AAPL"] > 0


async def test_graceful_shutdown_saves_state():
    """Test that graceful shutdown saves strategy state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = create_test_config(tmpdir)

        # First orchestrator session
        orchestrator1 = Orchestrator(config)

        # Send some data to build state
        orchestrator1.event_bus.publish(make_price_event("AAPL", 185.5))

        # Stop (saves state)
        orchestrator1.stop()

        # Second orchestrator session - should restore state
        orchestrator2 = Orchestrator(config)

        strategy = orchestrator2.strategies[0]
        assert "AAPL" in strategy._prices
        assert strategy._prices["AAPL"] == 185.5


async def test_orchestrator_start_stop_lifecycle():
    """Test orchestrator start/stop lifecycle."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = create_test_config(tmpdir)
        orchestrator = Orchestrator(config)

        assert not orchestrator.is_running

        orchestrator.start()
        assert orchestrator.is_running

        orchestrator.stop()
        assert not orchestrator.is_running


async def test_multiple_strategies_receive_events():
    """Test that multiple strategies all receive events."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = Config(
            ibkr=IBKRConfig(host="127.0.0.1", port=7497, client_id=1),
            data_store=DataStoreConfig(backend="file", path=tmpdir),
            collector=CollectorConfig(watchlist=["AAPL"], fundamental_refresh_hours=24),
            strategies=[
                StrategyConfig(
                    name="strategy_1",
                    class_path="src.strategies.example_value.ExampleValueStrategy",
                    allocated_capital=10000,
                    enabled=True,
                    params={"min_market_cap": 1_000_000_000},
                ),
                StrategyConfig(
                    name="strategy_2",
                    class_path="src.strategies.example_value.ExampleValueStrategy",
                    allocated_capital=5000,
                    enabled=True,
                    params={"min_market_cap": 500_000_000},
                ),
            ],
        )

        orchestrator = Orchestrator(config)
        assert len(orchestrator.strategies) == 2

        # Send price event
        orchestrator.event_bus.publish(make_price_event("AAPL", 185.5))

        # Both strategies should have received the price
        for strategy in orchestrator.strategies:
            assert "AAPL" in strategy._prices
            assert strategy._prices["AAPL"] == 185.5
