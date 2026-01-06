"""Strategy layer pipeline runner."""
import logging
from typing import Any

from src.strategies.base import StrategyLayer

logger = logging.getLogger(__name__)


class StrategyPipeline:
    """Runs data through a sequence of strategy layers.

    Each layer can analyze and enrich the data, and decide whether
    to pass to the next layer. Processing stops at the first layer
    that returns passed=False.
    """

    def __init__(self, layers: list[StrategyLayer]):
        """Initialize the pipeline.

        Args:
            layers: List of layers to run in sequence
        """
        self.layers = layers

    def run(self, symbol: str, initial_data: dict) -> tuple[bool, dict, str]:
        """Run data through all layers.

        Args:
            symbol: The symbol being analyzed
            initial_data: Starting data dict

        Returns:
            Tuple of (passed_all_layers, final_data, accumulated_reasoning)
        """
        if not self.layers:
            return True, initial_data, ""

        data = initial_data.copy()
        reasoning_parts: list[str] = []

        for layer in self.layers:
            logger.debug(f"Running layer '{layer.name}' for {symbol}")

            result = layer.process(symbol, data)

            # Accumulate reasoning
            reasoning_parts.append(f"[{layer.name}] {result.reasoning}")

            # Update data with layer's modifications
            data = result.data

            if not result.passed:
                logger.debug(f"Layer '{layer.name}' rejected {symbol}: {result.reasoning}")
                accumulated_reasoning = "\n".join(reasoning_parts)
                return False, data, accumulated_reasoning

            logger.debug(f"Layer '{layer.name}' passed {symbol}")

        accumulated_reasoning = "\n".join(reasoning_parts)
        return True, data, accumulated_reasoning
