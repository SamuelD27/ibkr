# Phase 3: Strategy Framework - TDD Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Define strategy protocols, implement layer pipeline runner, create example strategy

**Architecture:** Protocol-based strategies with layered processing pipeline

**Tech Stack:** Python 3.12+, typing.Protocol, dataclasses

---

## Task 1: Strategy Base Classes (Protocols)

**Files:**
- Create: `src/strategies/base.py`
- Test: `tests/unit/test_strategy_base.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_strategy_base.py
import pytest
from typing import Protocol, runtime_checkable


def test_strategy_layer_is_protocol():
    from src.strategies.base import StrategyLayer

    assert hasattr(StrategyLayer, '_is_protocol') or hasattr(StrategyLayer, '__protocol_attrs__')


def test_strategy_is_protocol():
    from src.strategies.base import Strategy

    assert hasattr(Strategy, '_is_protocol') or hasattr(Strategy, '__protocol_attrs__')


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
```

**Step 2-5:** Run test (fail), implement, run test (pass), commit.

---

## Task 2: Layer Pipeline Runner

**Files:**
- Create: `src/strategies/pipeline.py`
- Test: `tests/unit/test_pipeline.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_pipeline.py
import pytest
from src.models import LayerResult


class PassingLayer:
    name = "passing_layer"

    def process(self, symbol: str, data: dict) -> LayerResult:
        data["processed_by"] = data.get("processed_by", []) + [self.name]
        return LayerResult(passed=True, data=data, reasoning="Passed")


class FailingLayer:
    name = "failing_layer"

    def process(self, symbol: str, data: dict) -> LayerResult:
        return LayerResult(passed=False, data=data, reasoning="Failed check")


def test_pipeline_all_pass():
    from src.strategies.pipeline import StrategyPipeline

    pipeline = StrategyPipeline(layers=[PassingLayer(), PassingLayer()])

    passed, final_data, reasoning = pipeline.run("AAPL", {})

    assert passed is True
    assert final_data["processed_by"] == ["passing_layer", "passing_layer"]


def test_pipeline_stops_at_failure():
    from src.strategies.pipeline import StrategyPipeline

    pipeline = StrategyPipeline(layers=[PassingLayer(), FailingLayer(), PassingLayer()])

    passed, final_data, reasoning = pipeline.run("AAPL", {})

    assert passed is False
    assert "processed_by" in final_data
    assert len(final_data["processed_by"]) == 1  # Only first layer ran


def test_pipeline_accumulates_reasoning():
    from src.strategies.pipeline import StrategyPipeline

    pipeline = StrategyPipeline(layers=[PassingLayer(), PassingLayer()])

    passed, final_data, reasoning = pipeline.run("AAPL", {})

    assert "passing_layer" in reasoning
    assert reasoning.count("Passed") == 2


def test_pipeline_empty_layers():
    from src.strategies.pipeline import StrategyPipeline

    pipeline = StrategyPipeline(layers=[])

    passed, final_data, reasoning = pipeline.run("AAPL", {"initial": True})

    assert passed is True
    assert final_data == {"initial": True}
```

**Step 2-5:** Run test (fail), implement, run test (pass), commit.

---

## Task 3: Example Value Strategy

**Files:**
- Create: `src/strategies/example_value/__init__.py`
- Create: `src/strategies/example_value/strategy.py`
- Create: `src/strategies/example_value/layers/__init__.py`
- Create: `src/strategies/example_value/layers/liquidity_screen.py`
- Create: `src/strategies/example_value/layers/decision.py`
- Test: `tests/unit/test_example_value_strategy.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_example_value_strategy.py
import pytest
from datetime import datetime
from src.models import Event, FundamentalData


def test_liquidity_screen_passes_high_market_cap():
    from src.strategies.example_value.layers.liquidity_screen import LiquidityScreen

    layer = LiquidityScreen(min_market_cap=1_000_000_000)

    data = {
        "fundamental": FundamentalData(
            symbol="AAPL",
            timestamp=datetime.now(),
            company_name="Apple Inc",
            cik="123",
            employees=166000,
            shares_outstanding=15_000_000_000,
            float_shares=14_000_000_000,
            industry="Technology",
            category=None,
            subcategory=None,
            raw_xml="",
        ),
        "price": 150.0,
    }

    result = layer.process("AAPL", data)

    assert result.passed is True
    assert "market_cap" in data


def test_liquidity_screen_fails_low_market_cap():
    from src.strategies.example_value.layers.liquidity_screen import LiquidityScreen

    layer = LiquidityScreen(min_market_cap=1_000_000_000_000)  # 1T threshold

    data = {
        "fundamental": FundamentalData(
            symbol="SMALL",
            timestamp=datetime.now(),
            company_name="Small Corp",
            cik="456",
            employees=100,
            shares_outstanding=1_000_000,
            float_shares=900_000,
            industry="Technology",
            category=None,
            subcategory=None,
            raw_xml="",
        ),
        "price": 10.0,
    }

    result = layer.process("SMALL", data)

    assert result.passed is False


def test_decision_layer_returns_hold():
    from src.strategies.example_value.layers.decision import DecisionLayer
    from src.models import Action

    layer = DecisionLayer()

    result = layer.process("AAPL", {"market_cap": 2_000_000_000_000})

    assert result.passed is True
    assert result.data["action"] == Action.HOLD


def test_example_strategy_processes_event():
    from src.strategies.example_value.strategy import ExampleValueStrategy
    from src.models import Event

    strategy = ExampleValueStrategy(allocated_capital=10000.0)

    event = Event(
        type="fundamental_data",
        symbol="AAPL",
        timestamp=datetime.now(),
        ingested_at=datetime.now(),
        source="ibkr",
        payload={
            "company_name": "Apple Inc",
            "employees": 166000,
            "shares_outstanding": 15_000_000_000,
        },
    )

    decisions = strategy.on_event(event)

    # Should return decisions (even if empty for HOLD)
    assert isinstance(decisions, list)
```

**Step 2-5:** Run test (fail), implement, run test (pass), commit.

---

## Implementation Order

1. **Strategy Base Classes** - Protocols that define the interface
2. **Layer Pipeline Runner** - Executes layers in sequence
3. **Example Value Strategy** - Uses pipeline with real layers

## Testing Strategy

- Unit tests mock minimal dependencies
- Layers tested independently
- Pipeline tested with mock layers
- Strategy tested with mock events
