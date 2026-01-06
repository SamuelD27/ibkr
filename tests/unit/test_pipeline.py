"""Tests for Strategy Pipeline Runner."""
import pytest
from src.models import LayerResult


class PassingLayer:
    """Test layer that always passes."""

    name = "passing_layer"

    def process(self, symbol: str, data: dict) -> LayerResult:
        data["processed_by"] = data.get("processed_by", []) + [self.name]
        return LayerResult(passed=True, data=data, reasoning="Passed")


class FailingLayer:
    """Test layer that always fails."""

    name = "failing_layer"

    def process(self, symbol: str, data: dict) -> LayerResult:
        return LayerResult(passed=False, data=data, reasoning="Failed check")


class EnrichingLayer:
    """Test layer that enriches data."""

    name = "enriching_layer"

    def process(self, symbol: str, data: dict) -> LayerResult:
        data["enriched"] = True
        data["symbol_processed"] = symbol
        return LayerResult(passed=True, data=data, reasoning=f"Enriched data for {symbol}")


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
    assert reasoning == ""


def test_pipeline_enriches_data():
    from src.strategies.pipeline import StrategyPipeline

    pipeline = StrategyPipeline(layers=[EnrichingLayer(), PassingLayer()])

    passed, final_data, reasoning = pipeline.run("MSFT", {})

    assert passed is True
    assert final_data["enriched"] is True
    assert final_data["symbol_processed"] == "MSFT"


def test_pipeline_failure_includes_reasoning():
    from src.strategies.pipeline import StrategyPipeline

    pipeline = StrategyPipeline(layers=[PassingLayer(), FailingLayer()])

    passed, final_data, reasoning = pipeline.run("AAPL", {})

    assert passed is False
    assert "Failed check" in reasoning
    assert "Passed" in reasoning  # First layer's reasoning included


def test_pipeline_single_layer_pass():
    from src.strategies.pipeline import StrategyPipeline

    pipeline = StrategyPipeline(layers=[PassingLayer()])

    passed, final_data, reasoning = pipeline.run("AAPL", {})

    assert passed is True


def test_pipeline_single_layer_fail():
    from src.strategies.pipeline import StrategyPipeline

    pipeline = StrategyPipeline(layers=[FailingLayer()])

    passed, final_data, reasoning = pipeline.run("AAPL", {})

    assert passed is False
