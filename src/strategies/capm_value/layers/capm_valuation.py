"""CAPM valuation layer for CAPM value strategy."""
import logging
import time

from src.models import LayerResult

logger = logging.getLogger(__name__)


class CAPMValuation:
    """Calculate expected return and alpha using CAPM.

    CAPM Formula:
        Expected Return = Risk-Free Rate + Beta * (Market Return - Risk-Free Rate)

    Alpha:
        Alpha = Actual Return - Expected Return
        Positive alpha = stock is undervalued (outperforming)
        Negative alpha = stock is overvalued (underperforming)
    """

    name = "capm_valuation"

    def __init__(
        self,
        risk_free_rate: float = 0.05,
        expected_market_return: float = 0.10,
        use_historical_market_return: bool = True,
    ):
        """Initialize the CAPM valuation layer.

        Args:
            risk_free_rate: Annual risk-free rate (default: 5% - typical T-bill rate)
            expected_market_return: Expected annual market return (default: 10%)
            use_historical_market_return: If True, use historical return from data
                                          instead of expected_market_return
        """
        self.risk_free_rate = risk_free_rate
        self.expected_market_return = expected_market_return
        self.use_historical_market_return = use_historical_market_return

        logger.debug(
            "INIT: CAPMValuation initialized",
            extra={
                "extra_data": {
                    "action": "layer_init",
                    "layer": self.name,
                    "risk_free_rate": risk_free_rate,
                    "expected_market_return": expected_market_return,
                    "use_historical_market_return": use_historical_market_return,
                }
            },
        )

    def process(self, symbol: str, data: dict) -> LayerResult:
        """Calculate expected return and alpha using CAPM.

        Args:
            symbol: Stock symbol
            data: Dict containing 'beta', 'avg_stock_return', and optionally
                  'avg_market_return' from previous layers

        Returns:
            LayerResult with CAPM metrics added to data
        """
        start_time = time.perf_counter()

        logger.debug(
            f"ENTER: CAPMValuation.process for {symbol}",
            extra={
                "extra_data": {
                    "action": "layer_entry",
                    "layer": self.name,
                    "symbol": symbol,
                    "data_keys": list(data.keys()),
                }
            },
        )

        # Get required inputs
        beta: float | None = data.get("beta")
        avg_stock_return: float | None = data.get("avg_stock_return")

        if beta is None:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(
                f"EXIT: CAPMValuation.process - missing beta",
                extra={
                    "extra_data": {
                        "action": "layer_exit",
                        "layer": self.name,
                        "symbol": symbol,
                        "passed": False,
                        "reason": "missing_beta",
                        "elapsed_ms": elapsed_ms,
                    }
                },
            )
            return LayerResult(
                passed=False,
                data=data,
                reasoning=f"Missing beta for {symbol} CAPM calculation",
            )

        if avg_stock_return is None:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(
                f"EXIT: CAPMValuation.process - missing avg_stock_return",
                extra={
                    "extra_data": {
                        "action": "layer_exit",
                        "layer": self.name,
                        "symbol": symbol,
                        "passed": False,
                        "reason": "missing_avg_stock_return",
                        "elapsed_ms": elapsed_ms,
                    }
                },
            )
            return LayerResult(
                passed=False,
                data=data,
                reasoning=f"Missing average stock return for {symbol} CAPM calculation",
            )

        # Determine market return to use
        if self.use_historical_market_return and "avg_market_return" in data:
            market_return = data["avg_market_return"]
            market_return_source = "historical"
        else:
            market_return = self.expected_market_return
            market_return_source = "expected"

        logger.debug(
            f"STEP 1/3: Determining market return for {symbol}",
            extra={
                "extra_data": {
                    "action": "processing_step",
                    "step": "market_return",
                    "step_number": 1,
                    "total_steps": 3,
                    "symbol": symbol,
                    "market_return": market_return,
                    "source": market_return_source,
                    "use_historical": self.use_historical_market_return,
                }
            },
        )

        # Calculate market risk premium
        market_risk_premium = market_return - self.risk_free_rate

        logger.debug(
            f"STEP 2/3: Calculating CAPM expected return for {symbol}",
            extra={
                "extra_data": {
                    "action": "processing_step",
                    "step": "expected_return",
                    "step_number": 2,
                    "total_steps": 3,
                    "symbol": symbol,
                    "risk_free_rate": self.risk_free_rate,
                    "market_return": market_return,
                    "market_risk_premium": market_risk_premium,
                    "beta": beta,
                }
            },
        )

        # CAPM Expected Return = Rf + Beta * (Rm - Rf)
        expected_return = self.risk_free_rate + beta * market_risk_premium

        logger.debug(
            f"TRANSFORM: CAPM expected return for {symbol}",
            extra={
                "extra_data": {
                    "action": "transform_output",
                    "transform": "capm_expected_return",
                    "symbol": symbol,
                    "formula": "Rf + Beta * (Rm - Rf)",
                    "inputs": {
                        "Rf": self.risk_free_rate,
                        "Beta": beta,
                        "Rm": market_return,
                        "Rm_minus_Rf": market_risk_premium,
                    },
                    "expected_return": expected_return,
                }
            },
        )

        # Calculate Alpha = Actual Return - Expected Return
        logger.debug(
            f"STEP 3/3: Calculating alpha for {symbol}",
            extra={
                "extra_data": {
                    "action": "processing_step",
                    "step": "alpha",
                    "step_number": 3,
                    "total_steps": 3,
                    "symbol": symbol,
                    "actual_return": avg_stock_return,
                    "expected_return": expected_return,
                }
            },
        )

        alpha = avg_stock_return - expected_return

        # Determine if stock is overvalued or undervalued
        if alpha > 0:
            valuation = "undervalued"
            valuation_reasoning = f"outperforming by {alpha:.1%}"
        elif alpha < 0:
            valuation = "overvalued"
            valuation_reasoning = f"underperforming by {abs(alpha):.1%}"
        else:
            valuation = "fair_valued"
            valuation_reasoning = "performing as expected"

        logger.debug(
            f"TRANSFORM: Alpha calculation for {symbol}",
            extra={
                "extra_data": {
                    "action": "transform_output",
                    "transform": "alpha_calculation",
                    "symbol": symbol,
                    "formula": "Actual_Return - Expected_Return",
                    "inputs": {
                        "actual_return": avg_stock_return,
                        "expected_return": expected_return,
                    },
                    "alpha": alpha,
                    "valuation": valuation,
                }
            },
        )

        # Calculate Sharpe ratio (risk-adjusted return)
        stock_volatility = data.get("stock_volatility", 0)
        if stock_volatility > 0:
            sharpe_ratio = (avg_stock_return - self.risk_free_rate) / stock_volatility
        else:
            sharpe_ratio = 0.0

        # Store all CAPM results
        data["expected_return"] = expected_return
        data["alpha"] = alpha
        data["market_risk_premium"] = market_risk_premium
        data["market_return_used"] = market_return
        data["market_return_source"] = market_return_source
        data["risk_free_rate"] = self.risk_free_rate
        data["valuation"] = valuation
        data["sharpe_ratio"] = sharpe_ratio

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        logger.debug(
            f"EXIT: CAPMValuation.process - CAPM calculation complete",
            extra={
                "extra_data": {
                    "action": "layer_exit",
                    "layer": self.name,
                    "symbol": symbol,
                    "passed": True,
                    "results": {
                        "expected_return": expected_return,
                        "actual_return": avg_stock_return,
                        "alpha": alpha,
                        "beta": beta,
                        "sharpe_ratio": sharpe_ratio,
                        "valuation": valuation,
                    },
                    "elapsed_ms": elapsed_ms,
                }
            },
        )

        logger.info(
            f"{symbol} CAPM: alpha={alpha:.1%}, expected={expected_return:.1%}, "
            f"actual={avg_stock_return:.1%}, beta={beta:.2f}, sharpe={sharpe_ratio:.2f}"
        )

        return LayerResult(
            passed=True,
            data=data,
            reasoning=(
                f"{symbol} CAPM analysis: alpha={alpha:.1%} ({valuation_reasoning}), "
                f"expected_return={expected_return:.1%}, actual_return={avg_stock_return:.1%}, "
                f"beta={beta:.2f}, sharpe={sharpe_ratio:.2f}"
            ),
        )
