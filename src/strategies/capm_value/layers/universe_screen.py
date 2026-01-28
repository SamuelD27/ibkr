"""Universe screen layer for CAPM value strategy."""
import logging
import time
from typing import Any

from src.models import LayerResult, FundamentalData

logger = logging.getLogger(__name__)


class UniverseScreen:
    """Screen stocks for inclusion in CAPM universe.

    Filters based on:
    - Minimum market cap (liquidity)
    - Minimum trading history (need enough data for beta calculation)
    - Sector inclusion/exclusion (optional)
    """

    name = "universe_screen"

    def __init__(
        self,
        min_market_cap: float = 500_000_000,
        min_history_days: int = 252,
        excluded_sectors: list[str] | None = None,
    ):
        """Initialize the universe screen.

        Args:
            min_market_cap: Minimum market cap in dollars (default: 500M)
            min_history_days: Minimum trading days required (default: 252 = 1 year)
            excluded_sectors: Sectors to exclude (e.g., ["Financial Services"])
        """
        self.min_market_cap = min_market_cap
        self.min_history_days = min_history_days
        self.excluded_sectors = excluded_sectors or []

        logger.debug(
            "INIT: UniverseScreen initialized",
            extra={
                "extra_data": {
                    "action": "layer_init",
                    "layer": self.name,
                    "min_market_cap": min_market_cap,
                    "min_history_days": min_history_days,
                    "excluded_sectors": self.excluded_sectors,
                }
            },
        )

    def process(self, symbol: str, data: dict) -> LayerResult:
        """Check if stock passes universe screening criteria.

        Args:
            symbol: Stock symbol
            data: Dict containing 'fundamental' (FundamentalData), 'price' (float),
                  and optionally 'price_history' (list of prices)

        Returns:
            LayerResult with screening results added to data
        """
        start_time = time.perf_counter()

        logger.debug(
            f"ENTER: UniverseScreen.process for {symbol}",
            extra={
                "extra_data": {
                    "action": "layer_entry",
                    "layer": self.name,
                    "symbol": symbol,
                    "data_keys": list(data.keys()),
                }
            },
        )

        fundamental: FundamentalData | None = data.get("fundamental")
        price: float | None = data.get("price")
        price_history: list[float] | None = data.get("price_history")

        # Track screening results
        screening_results: dict[str, Any] = {
            "market_cap_check": None,
            "history_check": None,
            "sector_check": None,
        }

        # Check for required data
        if fundamental is None:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(
                f"EXIT: UniverseScreen.process - missing fundamental data",
                extra={
                    "extra_data": {
                        "action": "layer_exit",
                        "layer": self.name,
                        "symbol": symbol,
                        "passed": False,
                        "reason": "missing_fundamental",
                        "elapsed_ms": elapsed_ms,
                    }
                },
            )
            return LayerResult(
                passed=False,
                data=data,
                reasoning=f"Missing fundamental data for {symbol}",
            )

        if price is None or price <= 0:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(
                f"EXIT: UniverseScreen.process - missing/invalid price",
                extra={
                    "extra_data": {
                        "action": "layer_exit",
                        "layer": self.name,
                        "symbol": symbol,
                        "passed": False,
                        "reason": "missing_price",
                        "price": price,
                        "elapsed_ms": elapsed_ms,
                    }
                },
            )
            return LayerResult(
                passed=False,
                data=data,
                reasoning=f"Missing or invalid price for {symbol}: {price}",
            )

        # Check 1: Market cap
        logger.debug(
            f"STEP 1/3: Checking market cap for {symbol}",
            extra={
                "extra_data": {
                    "action": "screening_step",
                    "step": "market_cap",
                    "step_number": 1,
                    "total_steps": 3,
                    "symbol": symbol,
                }
            },
        )

        if fundamental.shares_outstanding is None:
            screening_results["market_cap_check"] = "missing_shares"
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(
                f"EXIT: UniverseScreen.process - missing shares outstanding",
                extra={
                    "extra_data": {
                        "action": "layer_exit",
                        "layer": self.name,
                        "symbol": symbol,
                        "passed": False,
                        "reason": "missing_shares_outstanding",
                        "elapsed_ms": elapsed_ms,
                    }
                },
            )
            return LayerResult(
                passed=False,
                data=data,
                reasoning=f"Missing shares outstanding for {symbol}",
            )

        market_cap = price * fundamental.shares_outstanding
        data["market_cap"] = market_cap
        screening_results["market_cap"] = market_cap

        logger.debug(
            f"DECISION: Market cap evaluation for {symbol}",
            extra={
                "extra_data": {
                    "action": "decision_point",
                    "decision": "market_cap_threshold",
                    "symbol": symbol,
                    "market_cap": market_cap,
                    "threshold": self.min_market_cap,
                    "passed": market_cap >= self.min_market_cap,
                }
            },
        )

        if market_cap < self.min_market_cap:
            screening_results["market_cap_check"] = "below_threshold"
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(
                f"EXIT: UniverseScreen.process - market cap below threshold",
                extra={
                    "extra_data": {
                        "action": "layer_exit",
                        "layer": self.name,
                        "symbol": symbol,
                        "passed": False,
                        "reason": "market_cap_below_threshold",
                        "market_cap": market_cap,
                        "threshold": self.min_market_cap,
                        "elapsed_ms": elapsed_ms,
                    }
                },
            )
            return LayerResult(
                passed=False,
                data=data,
                reasoning=f"{symbol} market cap ${market_cap:,.0f} below threshold ${self.min_market_cap:,.0f}",
            )

        screening_results["market_cap_check"] = "passed"

        # Check 2: Trading history
        logger.debug(
            f"STEP 2/3: Checking trading history for {symbol}",
            extra={
                "extra_data": {
                    "action": "screening_step",
                    "step": "history",
                    "step_number": 2,
                    "total_steps": 3,
                    "symbol": symbol,
                }
            },
        )

        history_days = len(price_history) if price_history else 0
        data["history_days"] = history_days
        screening_results["history_days"] = history_days

        logger.debug(
            f"DECISION: Trading history evaluation for {symbol}",
            extra={
                "extra_data": {
                    "action": "decision_point",
                    "decision": "history_threshold",
                    "symbol": symbol,
                    "history_days": history_days,
                    "threshold": self.min_history_days,
                    "passed": history_days >= self.min_history_days,
                }
            },
        )

        if history_days < self.min_history_days:
            screening_results["history_check"] = "insufficient"
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(
                f"EXIT: UniverseScreen.process - insufficient history",
                extra={
                    "extra_data": {
                        "action": "layer_exit",
                        "layer": self.name,
                        "symbol": symbol,
                        "passed": False,
                        "reason": "insufficient_history",
                        "history_days": history_days,
                        "threshold": self.min_history_days,
                        "elapsed_ms": elapsed_ms,
                    }
                },
            )
            return LayerResult(
                passed=False,
                data=data,
                reasoning=f"{symbol} has {history_days} days history, need {self.min_history_days}",
            )

        screening_results["history_check"] = "passed"

        # Check 3: Sector exclusion
        logger.debug(
            f"STEP 3/3: Checking sector exclusion for {symbol}",
            extra={
                "extra_data": {
                    "action": "screening_step",
                    "step": "sector",
                    "step_number": 3,
                    "total_steps": 3,
                    "symbol": symbol,
                }
            },
        )

        sector = fundamental.industry or "Unknown"
        data["sector"] = sector
        screening_results["sector"] = sector

        logger.debug(
            f"DECISION: Sector exclusion evaluation for {symbol}",
            extra={
                "extra_data": {
                    "action": "decision_point",
                    "decision": "sector_exclusion",
                    "symbol": symbol,
                    "sector": sector,
                    "excluded_sectors": self.excluded_sectors,
                    "is_excluded": sector in self.excluded_sectors,
                }
            },
        )

        if sector in self.excluded_sectors:
            screening_results["sector_check"] = "excluded"
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(
                f"EXIT: UniverseScreen.process - sector excluded",
                extra={
                    "extra_data": {
                        "action": "layer_exit",
                        "layer": self.name,
                        "symbol": symbol,
                        "passed": False,
                        "reason": "sector_excluded",
                        "sector": sector,
                        "elapsed_ms": elapsed_ms,
                    }
                },
            )
            return LayerResult(
                passed=False,
                data=data,
                reasoning=f"{symbol} sector '{sector}' is excluded from universe",
            )

        screening_results["sector_check"] = "passed"

        # All checks passed
        data["screening_results"] = screening_results
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        logger.debug(
            f"EXIT: UniverseScreen.process - passed all screens",
            extra={
                "extra_data": {
                    "action": "layer_exit",
                    "layer": self.name,
                    "symbol": symbol,
                    "passed": True,
                    "screening_results": screening_results,
                    "elapsed_ms": elapsed_ms,
                }
            },
        )

        logger.info(
            f"{symbol} passed universe screen: market_cap=${market_cap:,.0f}, "
            f"history={history_days}d, sector={sector}"
        )

        return LayerResult(
            passed=True,
            data=data,
            reasoning=f"{symbol} passed universe screen (market_cap=${market_cap:,.0f}, history={history_days}d, sector={sector})",
        )
