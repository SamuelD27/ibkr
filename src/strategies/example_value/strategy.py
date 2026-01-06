"""Example value strategy implementation."""
import logging
from datetime import datetime

from src.models import Event, Decision, Action, FundamentalData
from src.strategies.base import Position
from src.strategies.pipeline import StrategyPipeline
from src.strategies.example_value.layers import LiquidityScreen, DecisionLayer

logger = logging.getLogger(__name__)


class ExampleValueStrategy:
    """Example value strategy for testing the framework.

    This strategy:
    1. Screens stocks by market cap (liquidity)
    2. Always returns HOLD (no actual trading logic)

    Purpose: Validate the full pipeline works before building real strategies.
    """

    name = "example_value"
    subscriptions = ["fundamental_data", "price_bar"]

    def __init__(
        self,
        allocated_capital: float,
        min_market_cap: float = 1_000_000_000,
    ):
        """Initialize the example value strategy.

        Args:
            allocated_capital: Capital allocated to this strategy
            min_market_cap: Minimum market cap threshold (default: 1B)
        """
        self.allocated_capital = allocated_capital
        self.min_market_cap = min_market_cap

        # Build the layer pipeline
        self.pipeline = StrategyPipeline(
            layers=[
                LiquidityScreen(min_market_cap=min_market_cap),
                DecisionLayer(),
            ]
        )

        # Internal state
        self._positions: dict[str, Position] = {}
        self._fundamentals: dict[str, FundamentalData] = {}
        self._prices: dict[str, float] = {}

    def on_event(self, event: Event) -> list[Decision]:
        """Process an event through the strategy pipeline.

        Args:
            event: The event to process

        Returns:
            List of trading decisions (may be empty)
        """
        if event.symbol is None:
            return []

        symbol = event.symbol

        # Update internal state based on event type
        if event.type == "price_bar":
            self._prices[symbol] = event.payload.get("close", 0)
            logger.debug(f"Updated price for {symbol}: {self._prices[symbol]}")

        elif event.type == "fundamental_data":
            # Store fundamental data from event payload
            payload = event.payload
            self._fundamentals[symbol] = FundamentalData(
                symbol=symbol,
                timestamp=event.timestamp,
                company_name=payload.get("company_name", ""),
                cik=payload.get("cik", ""),
                employees=payload.get("employees"),
                shares_outstanding=payload.get("shares_outstanding"),
                float_shares=payload.get("float_shares"),
                industry=payload.get("industry"),
                category=payload.get("category"),
                subcategory=payload.get("subcategory"),
                raw_xml=payload.get("raw_xml", ""),
            )
            logger.debug(f"Stored fundamental data for {symbol}")

        # Check if we have all required data to run pipeline
        if symbol not in self._fundamentals or symbol not in self._prices:
            logger.debug(f"Missing data for {symbol}, skipping pipeline")
            return []

        # Build data dict for pipeline
        data = {
            "fundamental": self._fundamentals[symbol],
            "price": self._prices[symbol],
        }

        # Run through pipeline
        passed, final_data, reasoning = self.pipeline.run(symbol, data)

        logger.info(f"Pipeline result for {symbol}: passed={passed}")
        logger.debug(f"Reasoning:\n{reasoning}")

        # Generate decision if pipeline passed
        if passed:
            action = final_data.get("action", Action.HOLD)
            decision = Decision(
                symbol=symbol,
                action=action,
                target_weight=0.0,  # HOLD means no change
                confidence=1.0,
                reasoning=reasoning,
            )
            return [decision]

        return []

    def get_positions(self) -> dict[str, Position]:
        """Get current positions held by this strategy."""
        return self._positions.copy()

    def get_state(self) -> dict:
        """Get serializable state for persistence."""
        return {
            "prices": self._prices.copy(),
            "positions": {
                symbol: {
                    "symbol": pos.symbol,
                    "quantity": pos.quantity,
                    "avg_cost": pos.avg_cost,
                    "current_price": pos.current_price,
                }
                for symbol, pos in self._positions.items()
            },
        }

    def load_state(self, state: dict) -> None:
        """Restore strategy from saved state."""
        self._prices = state.get("prices", {})

        positions_data = state.get("positions", {})
        self._positions = {
            symbol: Position(
                symbol=pos_data["symbol"],
                quantity=pos_data["quantity"],
                avg_cost=pos_data["avg_cost"],
                current_price=pos_data["current_price"],
            )
            for symbol, pos_data in positions_data.items()
        }

        logger.info(f"Restored state: {len(self._prices)} prices, {len(self._positions)} positions")
