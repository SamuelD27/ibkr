"""Decision layer for CAPM value strategy."""
import logging
import time

from src.models import LayerResult, Action

logger = logging.getLogger(__name__)


class CAPMDecision:
    """Make trading decisions based on CAPM alpha.

    Decision logic:
    - BUY: Alpha > buy_threshold (stock is significantly undervalued)
    - EXIT: Alpha < exit_threshold (stock is significantly overvalued)
    - HOLD: Otherwise (stock is fairly valued)

    Additional filters:
    - Minimum Sharpe ratio for BUY signals
    - Maximum position weight based on conviction
    """

    name = "capm_decision"

    def __init__(
        self,
        buy_alpha_threshold: float = 0.02,
        exit_alpha_threshold: float = -0.02,
        min_sharpe_for_buy: float = 0.5,
        max_position_weight: float = 0.10,
        confidence_scaling: bool = True,
    ):
        """Initialize the CAPM decision layer.

        Args:
            buy_alpha_threshold: Minimum alpha to trigger BUY (default: 2%)
            exit_alpha_threshold: Alpha below this triggers EXIT (default: -2%)
            min_sharpe_for_buy: Minimum Sharpe ratio for BUY (default: 0.5)
            max_position_weight: Maximum portfolio weight per position (default: 10%)
            confidence_scaling: Scale position size by alpha magnitude
        """
        self.buy_alpha_threshold = buy_alpha_threshold
        self.exit_alpha_threshold = exit_alpha_threshold
        self.min_sharpe_for_buy = min_sharpe_for_buy
        self.max_position_weight = max_position_weight
        self.confidence_scaling = confidence_scaling

        logger.debug(
            "INIT: CAPMDecision initialized",
            extra={
                "extra_data": {
                    "action": "layer_init",
                    "layer": self.name,
                    "buy_alpha_threshold": buy_alpha_threshold,
                    "exit_alpha_threshold": exit_alpha_threshold,
                    "min_sharpe_for_buy": min_sharpe_for_buy,
                    "max_position_weight": max_position_weight,
                    "confidence_scaling": confidence_scaling,
                }
            },
        )

    def _calculate_target_weight(self, alpha: float, sharpe: float) -> float:
        """Calculate target position weight based on conviction.

        Args:
            alpha: CAPM alpha (positive = undervalued)
            sharpe: Sharpe ratio

        Returns:
            Target weight as fraction of portfolio (0.0 to max_position_weight)
        """
        if not self.confidence_scaling:
            return self.max_position_weight

        # Base weight scales with alpha magnitude
        # Alpha of 5% -> 50% of max weight
        # Alpha of 10% -> 100% of max weight
        alpha_factor = min(abs(alpha) / 0.10, 1.0)

        # Sharpe bonus: higher Sharpe = more confident
        # Sharpe of 1.0 -> 100% of alpha-based weight
        # Sharpe of 2.0 -> 120% of alpha-based weight (capped)
        sharpe_factor = min(max(sharpe, 0) / 1.0, 1.2)

        raw_weight = self.max_position_weight * alpha_factor * sharpe_factor
        target_weight = min(raw_weight, self.max_position_weight)

        logger.debug(
            "TRANSFORM: Target weight calculation",
            extra={
                "extra_data": {
                    "action": "transform_output",
                    "transform": "target_weight",
                    "alpha": alpha,
                    "sharpe": sharpe,
                    "alpha_factor": alpha_factor,
                    "sharpe_factor": sharpe_factor,
                    "raw_weight": raw_weight,
                    "target_weight": target_weight,
                    "max_position_weight": self.max_position_weight,
                }
            },
        )

        return target_weight

    def _calculate_confidence(self, alpha: float, sharpe: float) -> float:
        """Calculate confidence score for the decision.

        Args:
            alpha: CAPM alpha
            sharpe: Sharpe ratio

        Returns:
            Confidence score from 0.0 to 1.0
        """
        # Confidence based on:
        # 1. Alpha magnitude (how far from thresholds)
        # 2. Sharpe ratio (risk-adjusted quality)

        # Alpha contribution: further from 0 = more confident
        alpha_confidence = min(abs(alpha) / 0.05, 1.0)  # 5% alpha = max confidence

        # Sharpe contribution
        sharpe_confidence = min(max(sharpe, 0) / 2.0, 1.0)  # Sharpe 2 = max confidence

        # Combined confidence (weighted average)
        confidence = 0.6 * alpha_confidence + 0.4 * sharpe_confidence

        return round(confidence, 3)

    def process(self, symbol: str, data: dict) -> LayerResult:
        """Make trading decision based on CAPM metrics.

        Args:
            symbol: Stock symbol
            data: Dict containing 'alpha', 'sharpe_ratio', 'expected_return',
                  'beta', 'valuation' from previous layers

        Returns:
            LayerResult with 'action', 'target_weight', 'confidence' added to data
        """
        start_time = time.perf_counter()

        logger.debug(
            f"ENTER: CAPMDecision.process for {symbol}",
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
        alpha: float | None = data.get("alpha")
        sharpe_ratio: float | None = data.get("sharpe_ratio")
        beta: float | None = data.get("beta")
        valuation: str | None = data.get("valuation")

        if alpha is None:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(
                f"EXIT: CAPMDecision.process - missing alpha",
                extra={
                    "extra_data": {
                        "action": "layer_exit",
                        "layer": self.name,
                        "symbol": symbol,
                        "passed": False,
                        "reason": "missing_alpha",
                        "elapsed_ms": elapsed_ms,
                    }
                },
            )
            return LayerResult(
                passed=False,
                data=data,
                reasoning=f"Missing alpha for {symbol} decision",
            )

        sharpe = sharpe_ratio if sharpe_ratio is not None else 0.0

        # Log all inputs for decision
        logger.debug(
            f"STEP 1/3: Evaluating decision inputs for {symbol}",
            extra={
                "extra_data": {
                    "action": "processing_step",
                    "step": "evaluate_inputs",
                    "step_number": 1,
                    "total_steps": 3,
                    "symbol": symbol,
                    "inputs": {
                        "alpha": alpha,
                        "sharpe_ratio": sharpe,
                        "beta": beta,
                        "valuation": valuation,
                    },
                    "thresholds": {
                        "buy_alpha": self.buy_alpha_threshold,
                        "exit_alpha": self.exit_alpha_threshold,
                        "min_sharpe_for_buy": self.min_sharpe_for_buy,
                    },
                }
            },
        )

        # Decision tree
        logger.debug(
            f"STEP 2/3: Applying decision logic for {symbol}",
            extra={
                "extra_data": {
                    "action": "processing_step",
                    "step": "decision_logic",
                    "step_number": 2,
                    "total_steps": 3,
                    "symbol": symbol,
                }
            },
        )

        action: Action
        target_weight: float
        decision_reason: str

        # Check for BUY signal
        if alpha > self.buy_alpha_threshold:
            logger.debug(
                f"DECISION: Alpha above buy threshold for {symbol}",
                extra={
                    "extra_data": {
                        "action": "decision_point",
                        "decision": "alpha_above_buy_threshold",
                        "symbol": symbol,
                        "alpha": alpha,
                        "threshold": self.buy_alpha_threshold,
                        "branch": "potential_buy",
                    }
                },
            )

            # Additional Sharpe check
            if sharpe < self.min_sharpe_for_buy:
                logger.debug(
                    f"DECISION: Sharpe below minimum for BUY for {symbol}",
                    extra={
                        "extra_data": {
                            "action": "decision_point",
                            "decision": "sharpe_check",
                            "symbol": symbol,
                            "sharpe": sharpe,
                            "min_sharpe": self.min_sharpe_for_buy,
                            "branch": "hold_due_to_sharpe",
                        }
                    },
                )
                action = Action.HOLD
                target_weight = 0.0
                decision_reason = (
                    f"Alpha {alpha:.1%} suggests BUY but Sharpe {sharpe:.2f} "
                    f"< min {self.min_sharpe_for_buy}"
                )
            else:
                action = Action.BUY
                target_weight = self._calculate_target_weight(alpha, sharpe)
                decision_reason = (
                    f"BUY: Alpha {alpha:.1%} > {self.buy_alpha_threshold:.1%}, "
                    f"Sharpe {sharpe:.2f}, target_weight={target_weight:.1%}"
                )

        # Check for EXIT signal
        elif alpha < self.exit_alpha_threshold:
            logger.debug(
                f"DECISION: Alpha below exit threshold for {symbol}",
                extra={
                    "extra_data": {
                        "action": "decision_point",
                        "decision": "alpha_below_exit_threshold",
                        "symbol": symbol,
                        "alpha": alpha,
                        "threshold": self.exit_alpha_threshold,
                        "branch": "exit",
                    }
                },
            )
            action = Action.EXIT
            target_weight = 0.0
            decision_reason = (
                f"EXIT: Alpha {alpha:.1%} < {self.exit_alpha_threshold:.1%} "
                f"(underperforming CAPM expectation)"
            )

        # HOLD - alpha within neutral zone
        else:
            logger.debug(
                f"DECISION: Alpha in neutral zone for {symbol}",
                extra={
                    "extra_data": {
                        "action": "decision_point",
                        "decision": "alpha_in_neutral_zone",
                        "symbol": symbol,
                        "alpha": alpha,
                        "exit_threshold": self.exit_alpha_threshold,
                        "buy_threshold": self.buy_alpha_threshold,
                        "branch": "hold",
                    }
                },
            )
            action = Action.HOLD
            target_weight = 0.0
            decision_reason = (
                f"HOLD: Alpha {alpha:.1%} in neutral zone "
                f"[{self.exit_alpha_threshold:.1%}, {self.buy_alpha_threshold:.1%}]"
            )

        # Calculate confidence
        logger.debug(
            f"STEP 3/3: Calculating confidence for {symbol}",
            extra={
                "extra_data": {
                    "action": "processing_step",
                    "step": "confidence",
                    "step_number": 3,
                    "total_steps": 3,
                    "symbol": symbol,
                }
            },
        )

        confidence = self._calculate_confidence(alpha, sharpe)

        # Store decision in data
        data["action"] = action
        data["target_weight"] = target_weight
        data["confidence"] = confidence
        data["decision_reason"] = decision_reason

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        logger.debug(
            f"EXIT: CAPMDecision.process - decision made",
            extra={
                "extra_data": {
                    "action": "layer_exit",
                    "layer": self.name,
                    "symbol": symbol,
                    "passed": True,
                    "decision": {
                        "action": action.value,
                        "target_weight": target_weight,
                        "confidence": confidence,
                        "reason": decision_reason,
                    },
                    "inputs": {
                        "alpha": alpha,
                        "sharpe": sharpe,
                        "beta": beta,
                    },
                    "elapsed_ms": elapsed_ms,
                }
            },
        )

        logger.info(
            f"{symbol} CAPM decision: {action.value.upper()} "
            f"(alpha={alpha:.1%}, weight={target_weight:.1%}, confidence={confidence:.0%})"
        )

        return LayerResult(
            passed=True,
            data=data,
            reasoning=f"{symbol}: {decision_reason} | confidence={confidence:.0%}",
        )
