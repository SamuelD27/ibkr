"""Beta calculation layer for CAPM value strategy."""
import logging
import time
from typing import Any

from src.models import LayerResult

logger = logging.getLogger(__name__)


class BetaCalculator:
    """Calculate stock beta relative to market benchmark.

    Beta = Covariance(stock_returns, market_returns) / Variance(market_returns)

    Beta interpretation:
    - Beta = 1: Stock moves with market
    - Beta > 1: Stock is more volatile than market
    - Beta < 1: Stock is less volatile than market
    - Beta < 0: Stock moves opposite to market (rare)
    """

    name = "beta_calculator"

    def __init__(
        self,
        lookback_days: int = 252,
        min_beta: float = 0.0,
        max_beta: float = 3.0,
    ):
        """Initialize the beta calculator.

        Args:
            lookback_days: Number of days to use for beta calculation (default: 252 = 1 year)
            min_beta: Minimum acceptable beta (default: 0.0)
            max_beta: Maximum acceptable beta (default: 3.0)
        """
        self.lookback_days = lookback_days
        self.min_beta = min_beta
        self.max_beta = max_beta

        logger.debug(
            "INIT: BetaCalculator initialized",
            extra={
                "extra_data": {
                    "action": "layer_init",
                    "layer": self.name,
                    "lookback_days": lookback_days,
                    "min_beta": min_beta,
                    "max_beta": max_beta,
                }
            },
        )

    def _calculate_returns(self, prices: list[float]) -> list[float]:
        """Calculate daily returns from price series.

        Args:
            prices: List of prices (oldest first)

        Returns:
            List of daily returns
        """
        if len(prices) < 2:
            return []

        returns = []
        for i in range(1, len(prices)):
            if prices[i - 1] != 0:
                daily_return = (prices[i] - prices[i - 1]) / prices[i - 1]
                returns.append(daily_return)

        logger.debug(
            "TRANSFORM: Calculated returns from prices",
            extra={
                "extra_data": {
                    "action": "transform_output",
                    "transform": "price_to_returns",
                    "input_count": len(prices),
                    "output_count": len(returns),
                    "avg_return": sum(returns) / len(returns) if returns else 0,
                }
            },
        )

        return returns

    def _calculate_covariance(self, x: list[float], y: list[float]) -> float:
        """Calculate covariance between two series.

        Args:
            x: First series
            y: Second series

        Returns:
            Covariance value
        """
        if len(x) != len(y) or len(x) == 0:
            return 0.0

        n = len(x)
        mean_x = sum(x) / n
        mean_y = sum(y) / n

        covariance = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / (n - 1)

        return covariance

    def _calculate_variance(self, x: list[float]) -> float:
        """Calculate variance of a series.

        Args:
            x: Data series

        Returns:
            Variance value
        """
        if len(x) < 2:
            return 0.0

        n = len(x)
        mean = sum(x) / n
        variance = sum((xi - mean) ** 2 for xi in x) / (n - 1)

        return variance

    def process(self, symbol: str, data: dict) -> LayerResult:
        """Calculate beta for stock relative to market.

        Args:
            symbol: Stock symbol
            data: Dict containing 'price_history' (stock prices) and
                  'market_history' (market benchmark prices)

        Returns:
            LayerResult with beta added to data
        """
        start_time = time.perf_counter()

        logger.debug(
            f"ENTER: BetaCalculator.process for {symbol}",
            extra={
                "extra_data": {
                    "action": "layer_entry",
                    "layer": self.name,
                    "symbol": symbol,
                    "data_keys": list(data.keys()),
                }
            },
        )

        price_history: list[float] | None = data.get("price_history")
        market_history: list[float] | None = data.get("market_history")

        # Check for required data
        if price_history is None or len(price_history) < 2:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(
                f"EXIT: BetaCalculator.process - insufficient price history",
                extra={
                    "extra_data": {
                        "action": "layer_exit",
                        "layer": self.name,
                        "symbol": symbol,
                        "passed": False,
                        "reason": "insufficient_price_history",
                        "history_length": len(price_history) if price_history else 0,
                        "elapsed_ms": elapsed_ms,
                    }
                },
            )
            return LayerResult(
                passed=False,
                data=data,
                reasoning=f"Insufficient price history for {symbol} beta calculation",
            )

        if market_history is None or len(market_history) < 2:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(
                f"EXIT: BetaCalculator.process - insufficient market history",
                extra={
                    "extra_data": {
                        "action": "layer_exit",
                        "layer": self.name,
                        "symbol": symbol,
                        "passed": False,
                        "reason": "insufficient_market_history",
                        "history_length": len(market_history) if market_history else 0,
                        "elapsed_ms": elapsed_ms,
                    }
                },
            )
            return LayerResult(
                passed=False,
                data=data,
                reasoning=f"Insufficient market history for {symbol} beta calculation",
            )

        # Align histories to lookback period
        lookback = min(self.lookback_days, len(price_history), len(market_history))

        logger.debug(
            f"STEP 1/3: Aligning price histories for {symbol}",
            extra={
                "extra_data": {
                    "action": "processing_step",
                    "step": "align_histories",
                    "step_number": 1,
                    "total_steps": 3,
                    "symbol": symbol,
                    "stock_history_len": len(price_history),
                    "market_history_len": len(market_history),
                    "using_lookback": lookback,
                }
            },
        )

        stock_prices = price_history[-lookback:]
        market_prices = market_history[-lookback:]

        # Calculate returns
        logger.debug(
            f"STEP 2/3: Calculating returns for {symbol}",
            extra={
                "extra_data": {
                    "action": "processing_step",
                    "step": "calculate_returns",
                    "step_number": 2,
                    "total_steps": 3,
                    "symbol": symbol,
                }
            },
        )

        stock_returns = self._calculate_returns(stock_prices)
        market_returns = self._calculate_returns(market_prices)

        if len(stock_returns) != len(market_returns) or len(stock_returns) == 0:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(
                f"EXIT: BetaCalculator.process - returns mismatch",
                extra={
                    "extra_data": {
                        "action": "layer_exit",
                        "layer": self.name,
                        "symbol": symbol,
                        "passed": False,
                        "reason": "returns_mismatch",
                        "stock_returns_len": len(stock_returns),
                        "market_returns_len": len(market_returns),
                        "elapsed_ms": elapsed_ms,
                    }
                },
            )
            return LayerResult(
                passed=False,
                data=data,
                reasoning=f"Returns calculation failed for {symbol}",
            )

        # Calculate beta
        logger.debug(
            f"STEP 3/3: Calculating beta for {symbol}",
            extra={
                "extra_data": {
                    "action": "processing_step",
                    "step": "calculate_beta",
                    "step_number": 3,
                    "total_steps": 3,
                    "symbol": symbol,
                    "returns_count": len(stock_returns),
                }
            },
        )

        covariance = self._calculate_covariance(stock_returns, market_returns)
        market_variance = self._calculate_variance(market_returns)

        if market_variance == 0:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(
                f"EXIT: BetaCalculator.process - zero market variance",
                extra={
                    "extra_data": {
                        "action": "layer_exit",
                        "layer": self.name,
                        "symbol": symbol,
                        "passed": False,
                        "reason": "zero_market_variance",
                        "elapsed_ms": elapsed_ms,
                    }
                },
            )
            return LayerResult(
                passed=False,
                data=data,
                reasoning=f"Market variance is zero, cannot calculate beta for {symbol}",
            )

        beta = covariance / market_variance

        # Also calculate stock volatility (annualized)
        stock_variance = self._calculate_variance(stock_returns)
        stock_volatility = (stock_variance ** 0.5) * (252 ** 0.5)  # Annualize

        # Store results
        data["beta"] = beta
        data["stock_volatility"] = stock_volatility
        data["covariance"] = covariance
        data["market_variance"] = market_variance
        data["returns_count"] = len(stock_returns)

        # Calculate average returns (annualized)
        avg_stock_return = sum(stock_returns) / len(stock_returns) * 252
        avg_market_return = sum(market_returns) / len(market_returns) * 252
        data["avg_stock_return"] = avg_stock_return
        data["avg_market_return"] = avg_market_return

        logger.debug(
            f"TRANSFORM: Beta calculation results for {symbol}",
            extra={
                "extra_data": {
                    "action": "transform_output",
                    "transform": "beta_calculation",
                    "symbol": symbol,
                    "beta": beta,
                    "stock_volatility": stock_volatility,
                    "covariance": covariance,
                    "market_variance": market_variance,
                    "avg_stock_return": avg_stock_return,
                    "avg_market_return": avg_market_return,
                }
            },
        )

        # Check beta bounds
        logger.debug(
            f"DECISION: Beta bounds check for {symbol}",
            extra={
                "extra_data": {
                    "action": "decision_point",
                    "decision": "beta_bounds",
                    "symbol": symbol,
                    "beta": beta,
                    "min_beta": self.min_beta,
                    "max_beta": self.max_beta,
                    "within_bounds": self.min_beta <= beta <= self.max_beta,
                }
            },
        )

        if beta < self.min_beta:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(
                f"EXIT: BetaCalculator.process - beta below minimum",
                extra={
                    "extra_data": {
                        "action": "layer_exit",
                        "layer": self.name,
                        "symbol": symbol,
                        "passed": False,
                        "reason": "beta_below_minimum",
                        "beta": beta,
                        "min_beta": self.min_beta,
                        "elapsed_ms": elapsed_ms,
                    }
                },
            )
            return LayerResult(
                passed=False,
                data=data,
                reasoning=f"{symbol} beta {beta:.2f} below minimum {self.min_beta}",
            )

        if beta > self.max_beta:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(
                f"EXIT: BetaCalculator.process - beta above maximum",
                extra={
                    "extra_data": {
                        "action": "layer_exit",
                        "layer": self.name,
                        "symbol": symbol,
                        "passed": False,
                        "reason": "beta_above_maximum",
                        "beta": beta,
                        "max_beta": self.max_beta,
                        "elapsed_ms": elapsed_ms,
                    }
                },
            )
            return LayerResult(
                passed=False,
                data=data,
                reasoning=f"{symbol} beta {beta:.2f} above maximum {self.max_beta}",
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        logger.debug(
            f"EXIT: BetaCalculator.process - beta calculated successfully",
            extra={
                "extra_data": {
                    "action": "layer_exit",
                    "layer": self.name,
                    "symbol": symbol,
                    "passed": True,
                    "beta": beta,
                    "stock_volatility": stock_volatility,
                    "elapsed_ms": elapsed_ms,
                }
            },
        )

        logger.info(
            f"{symbol} beta calculated: {beta:.2f} (volatility: {stock_volatility:.1%})"
        )

        return LayerResult(
            passed=True,
            data=data,
            reasoning=f"{symbol} beta={beta:.2f}, volatility={stock_volatility:.1%} (using {len(stock_returns)} days)",
        )
