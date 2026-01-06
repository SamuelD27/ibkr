"""Decision layer for example value strategy."""
import logging

from src.models import LayerResult, Action

logger = logging.getLogger(__name__)


class DecisionLayer:
    """Final decision layer that produces trading action.

    For the example strategy, this always returns HOLD.
    A real strategy would implement actual trading logic here.
    """

    name = "decision_layer"

    def process(self, symbol: str, data: dict) -> LayerResult:
        """Make final trading decision.

        Args:
            symbol: Stock symbol
            data: Dict containing analysis from previous layers

        Returns:
            LayerResult with 'action' added to data
        """
        # Example strategy always holds - no actual trading logic
        data["action"] = Action.HOLD

        market_cap = data.get("market_cap", 0)

        logger.debug(f"{symbol} decision: HOLD (example strategy)")

        return LayerResult(
            passed=True,
            data=data,
            reasoning=f"{symbol} passed all screens, decision: HOLD (market cap: ${market_cap:,.0f})",
        )
