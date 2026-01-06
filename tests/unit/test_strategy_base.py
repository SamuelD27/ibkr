"""Tests for Strategy base classes and protocols."""
import pytest


def test_strategy_layer_is_protocol():
    from src.strategies.base import StrategyLayer

    assert hasattr(StrategyLayer, '_is_protocol') or hasattr(StrategyLayer, '__protocol_attrs__')


def test_strategy_is_protocol():
    from src.strategies.base import Strategy

    assert hasattr(Strategy, '_is_protocol') or hasattr(Strategy, '__protocol_attrs__')


def test_position_dataclass():
    from src.strategies.base import Position

    pos = Position(
        symbol="AAPL",
        quantity=100,
        avg_cost=150.0,
        current_price=155.0,
    )

    assert pos.symbol == "AAPL"
    assert pos.quantity == 100
    assert pos.market_value == 15500.0
    assert pos.unrealized_pnl == 500.0


def test_strategy_layer_implementation():
    from src.strategies.base import StrategyLayer
    from src.models import LayerResult

    class TestLayer:
        name = "test_layer"

        def process(self, symbol: str, data: dict) -> LayerResult:
            return LayerResult(passed=True, data={"test": 1}, reasoning="Test passed")

    layer = TestLayer()
    assert isinstance(layer, StrategyLayer)


def test_strategy_implementation():
    from src.strategies.base import Strategy, Position
    from src.models import Event, Decision

    class TestStrategy:
        name = "test_strategy"
        subscriptions = ["price_bar"]
        allocated_capital = 10000.0

        def on_event(self, event: Event) -> list[Decision]:
            return []

        def get_positions(self) -> dict[str, Position]:
            return {}

        def get_state(self) -> dict:
            return {}

        def load_state(self, state: dict) -> None:
            pass

    strategy = TestStrategy()
    assert isinstance(strategy, Strategy)


def test_incomplete_strategy_not_protocol():
    from src.strategies.base import Strategy

    class IncompleteStrategy:
        name = "incomplete"
        # Missing required methods

    incomplete = IncompleteStrategy()
    assert not isinstance(incomplete, Strategy)


def test_incomplete_layer_not_protocol():
    from src.strategies.base import StrategyLayer

    class IncompleteLayer:
        name = "incomplete"
        # Missing process method

    incomplete = IncompleteLayer()
    assert not isinstance(incomplete, StrategyLayer)
