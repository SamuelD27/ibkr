"""Tests for strategy models."""
import pytest


def test_layer_result_creation():
    from src.models.strategy import LayerResult

    result = LayerResult(
        passed=True,
        data={"market_cap": 3000000000000},
        reasoning="Market cap $3T exceeds minimum threshold"
    )

    assert result.passed is True
    assert result.data["market_cap"] == 3000000000000
    assert "threshold" in result.reasoning


def test_layer_result_failure():
    from src.models.strategy import LayerResult

    result = LayerResult(
        passed=False,
        data={"market_cap": 500000000},
        reasoning="Market cap $500M below minimum $1B threshold"
    )

    assert result.passed is False


def test_decision_creation():
    from src.models.strategy import Decision
    from src.models.orders import Action

    decision = Decision(
        symbol="AAPL",
        action=Action.BUY,
        target_weight=0.05,
        confidence=0.8,
        reasoning="Strong fundamentals, passes all screens"
    )

    assert decision.symbol == "AAPL"
    assert decision.action == Action.BUY
    assert decision.target_weight == 0.05
    assert decision.confidence == 0.8
