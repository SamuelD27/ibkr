"""Liquidity screen layer for example value strategy."""
import logging

from src.models import LayerResult, FundamentalData

logger = logging.getLogger(__name__)


class LiquidityScreen:
    """Screen stocks by market cap liquidity threshold.

    Passes stocks with market cap above the minimum threshold.
    Requires 'fundamental' and 'price' keys in data dict.
    """

    name = "liquidity_screen"

    def __init__(self, min_market_cap: float = 1_000_000_000):
        """Initialize the liquidity screen.

        Args:
            min_market_cap: Minimum market cap in dollars (default: 1B)
        """
        self.min_market_cap = min_market_cap

    def process(self, symbol: str, data: dict) -> LayerResult:
        """Check if stock meets liquidity requirements.

        Args:
            symbol: Stock symbol
            data: Dict containing 'fundamental' (FundamentalData) and 'price' (float)

        Returns:
            LayerResult with market_cap added to data
        """
        fundamental: FundamentalData | None = data.get("fundamental")
        price: float | None = data.get("price")

        # Check for required data
        if fundamental is None:
            return LayerResult(
                passed=False,
                data=data,
                reasoning=f"Missing fundamental data for {symbol}",
            )

        if price is None:
            return LayerResult(
                passed=False,
                data=data,
                reasoning=f"Missing price data for {symbol}",
            )

        # Check for shares outstanding
        if fundamental.shares_outstanding is None:
            return LayerResult(
                passed=False,
                data=data,
                reasoning=f"Missing shares outstanding for {symbol}",
            )

        # Calculate market cap
        market_cap = price * fundamental.shares_outstanding
        data["market_cap"] = market_cap

        # Check against threshold
        if market_cap < self.min_market_cap:
            return LayerResult(
                passed=False,
                data=data,
                reasoning=f"{symbol} market cap ${market_cap:,.0f} below threshold ${self.min_market_cap:,.0f}",
            )

        logger.debug(f"{symbol} passed liquidity screen with market cap ${market_cap:,.0f}")

        return LayerResult(
            passed=True,
            data=data,
            reasoning=f"{symbol} market cap ${market_cap:,.0f} above threshold ${self.min_market_cap:,.0f}",
        )
