"""Tests for Example Value Strategy."""
import pytest
from datetime import datetime
from src.models import Event, FundamentalData, Action


@pytest.fixture
def apple_fundamental():
    """Create Apple fundamental data fixture."""
    return FundamentalData(
        symbol="AAPL",
        timestamp=datetime.now(),
        company_name="Apple Inc",
        cik="0000320193",
        employees=166000,
        shares_outstanding=15_000_000_000,
        float_shares=14_000_000_000,
        industry="Technology",
        category=None,
        subcategory=None,
        raw_xml="",
    )


@pytest.fixture
def small_company_fundamental():
    """Create small company fundamental data fixture."""
    return FundamentalData(
        symbol="SMALL",
        timestamp=datetime.now(),
        company_name="Small Corp",
        cik="0000123456",
        employees=100,
        shares_outstanding=1_000_000,
        float_shares=900_000,
        industry="Technology",
        category=None,
        subcategory=None,
        raw_xml="",
    )


def test_liquidity_screen_passes_high_market_cap(apple_fundamental):
    from src.strategies.example_value.layers.liquidity_screen import LiquidityScreen

    layer = LiquidityScreen(min_market_cap=1_000_000_000)

    data = {
        "fundamental": apple_fundamental,
        "price": 150.0,
    }

    result = layer.process("AAPL", data)

    assert result.passed is True
    assert "market_cap" in data
    assert data["market_cap"] == 150.0 * 15_000_000_000


def test_liquidity_screen_fails_low_market_cap(small_company_fundamental):
    from src.strategies.example_value.layers.liquidity_screen import LiquidityScreen

    layer = LiquidityScreen(min_market_cap=1_000_000_000)  # 1B threshold

    data = {
        "fundamental": small_company_fundamental,
        "price": 10.0,
    }

    result = layer.process("SMALL", data)

    assert result.passed is False
    assert "market_cap" in data
    assert data["market_cap"] == 10.0 * 1_000_000


def test_liquidity_screen_handles_missing_shares():
    from src.strategies.example_value.layers.liquidity_screen import LiquidityScreen

    layer = LiquidityScreen(min_market_cap=1_000_000_000)

    data = {
        "fundamental": FundamentalData(
            symbol="TEST",
            timestamp=datetime.now(),
            company_name="Test Corp",
            cik="123",
            employees=None,
            shares_outstanding=None,  # Missing
            float_shares=None,
            industry=None,
            category=None,
            subcategory=None,
            raw_xml="",
        ),
        "price": 100.0,
    }

    result = layer.process("TEST", data)

    assert result.passed is False
    assert "missing shares" in result.reasoning.lower()


def test_decision_layer_returns_hold():
    from src.strategies.example_value.layers.decision import DecisionLayer

    layer = DecisionLayer()

    result = layer.process("AAPL", {"market_cap": 2_000_000_000_000})

    assert result.passed is True
    assert result.data["action"] == Action.HOLD


def test_example_strategy_creates_pipeline():
    from src.strategies.example_value.strategy import ExampleValueStrategy

    strategy = ExampleValueStrategy(allocated_capital=10000.0)

    assert strategy.name == "example_value"
    assert len(strategy.pipeline.layers) == 2


def test_example_strategy_subscriptions():
    from src.strategies.example_value.strategy import ExampleValueStrategy

    strategy = ExampleValueStrategy(allocated_capital=10000.0)

    assert "fundamental_data" in strategy.subscriptions
    assert "price_bar" in strategy.subscriptions


def test_example_strategy_processes_fundamental_event(apple_fundamental):
    from src.strategies.example_value.strategy import ExampleValueStrategy
    from src.models import Event

    strategy = ExampleValueStrategy(
        allocated_capital=10000.0,
        min_market_cap=1_000_000_000,
    )

    # Store price data first
    strategy._prices["AAPL"] = 150.0

    event = Event(
        type="fundamental_data",
        symbol="AAPL",
        timestamp=datetime.now(),
        ingested_at=datetime.now(),
        source="ibkr",
        payload={
            "company_name": apple_fundamental.company_name,
            "employees": apple_fundamental.employees,
            "shares_outstanding": apple_fundamental.shares_outstanding,
        },
    )

    # Store fundamental data
    strategy._fundamentals["AAPL"] = apple_fundamental

    decisions = strategy.on_event(event)

    assert isinstance(decisions, list)


def test_example_strategy_get_positions():
    from src.strategies.example_value.strategy import ExampleValueStrategy

    strategy = ExampleValueStrategy(allocated_capital=10000.0)

    positions = strategy.get_positions()

    assert isinstance(positions, dict)
    assert len(positions) == 0  # No positions initially


def test_example_strategy_state_persistence():
    from src.strategies.example_value.strategy import ExampleValueStrategy

    strategy = ExampleValueStrategy(allocated_capital=10000.0)
    strategy._prices["AAPL"] = 150.0

    # Save state
    state = strategy.get_state()

    # Create new strategy and restore
    new_strategy = ExampleValueStrategy(allocated_capital=10000.0)
    new_strategy.load_state(state)

    assert new_strategy._prices.get("AAPL") == 150.0
