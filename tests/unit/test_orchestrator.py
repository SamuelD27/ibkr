"""Tests for Orchestrator."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile


def create_mock_config():
    """Create a mock config for testing."""
    from src.core.config import Config, IBKRConfig, DataStoreConfig, CollectorConfig, StrategyConfig

    return Config(
        ibkr=IBKRConfig(host="127.0.0.1", port=7497, client_id=1),
        data_store=DataStoreConfig(backend="file", path="./data"),
        collector=CollectorConfig(watchlist=["AAPL", "MSFT"], fundamental_refresh_hours=24),
        strategies=[
            StrategyConfig(
                name="example_value",
                class_path="src.strategies.example_value.ExampleValueStrategy",
                allocated_capital=10000,
                enabled=True,
                params={"min_market_cap": 1000000000},
            )
        ],
    )


def test_orchestrator_init():
    from src.core.orchestrator import Orchestrator

    config = create_mock_config()
    orchestrator = Orchestrator(config)

    assert orchestrator.config is config
    assert not orchestrator.is_running


def test_orchestrator_initializes_event_bus():
    from src.core.orchestrator import Orchestrator

    config = create_mock_config()
    orchestrator = Orchestrator(config)

    assert orchestrator.event_bus is not None


def test_orchestrator_initializes_data_store():
    from src.core.orchestrator import Orchestrator

    with tempfile.TemporaryDirectory() as tmpdir:
        config = create_mock_config()
        config.data_store.path = tmpdir

        orchestrator = Orchestrator(config)

        assert orchestrator.data_store is not None


def test_orchestrator_loads_strategy():
    from src.core.orchestrator import Orchestrator

    with tempfile.TemporaryDirectory() as tmpdir:
        config = create_mock_config()
        config.data_store.path = tmpdir

        orchestrator = Orchestrator(config)

        assert len(orchestrator.strategies) == 1
        assert orchestrator.strategies[0].name == "example_value"


def test_orchestrator_skips_disabled_strategies():
    from src.core.orchestrator import Orchestrator
    from src.core.config import StrategyConfig

    with tempfile.TemporaryDirectory() as tmpdir:
        config = create_mock_config()
        config.data_store.path = tmpdir
        config.strategies.append(
            StrategyConfig(
                name="disabled_strategy",
                class_path="src.strategies.example_value.ExampleValueStrategy",
                allocated_capital=5000,
                enabled=False,
                params={},
            )
        )

        orchestrator = Orchestrator(config)

        assert len(orchestrator.strategies) == 1
        assert orchestrator.strategies[0].name == "example_value"


def test_orchestrator_subscribes_strategies_to_events():
    from src.core.orchestrator import Orchestrator

    with tempfile.TemporaryDirectory() as tmpdir:
        config = create_mock_config()
        config.data_store.path = tmpdir

        orchestrator = Orchestrator(config)

        # Check that event bus has subscribers
        assert len(orchestrator.event_bus._subscribers) > 0


def test_orchestrator_stop_sets_not_running():
    from src.core.orchestrator import Orchestrator

    with tempfile.TemporaryDirectory() as tmpdir:
        config = create_mock_config()
        config.data_store.path = tmpdir

        orchestrator = Orchestrator(config)
        orchestrator._running = True

        orchestrator.stop()

        assert not orchestrator.is_running


def test_orchestrator_saves_strategy_states_on_stop():
    from src.core.orchestrator import Orchestrator

    with tempfile.TemporaryDirectory() as tmpdir:
        config = create_mock_config()
        config.data_store.path = tmpdir

        orchestrator = Orchestrator(config)
        orchestrator._running = True

        # Set some state in the strategy
        orchestrator.strategies[0]._prices["AAPL"] = 150.0

        orchestrator.stop()

        # Verify state was saved
        saved_state = orchestrator.data_store.load_strategy_state("example_value")
        assert saved_state is not None
        assert saved_state["prices"]["AAPL"] == 150.0


def test_orchestrator_get_strategy_by_name():
    from src.core.orchestrator import Orchestrator

    with tempfile.TemporaryDirectory() as tmpdir:
        config = create_mock_config()
        config.data_store.path = tmpdir

        orchestrator = Orchestrator(config)

        strategy = orchestrator.get_strategy("example_value")
        assert strategy is not None
        assert strategy.name == "example_value"

        missing = orchestrator.get_strategy("nonexistent")
        assert missing is None
