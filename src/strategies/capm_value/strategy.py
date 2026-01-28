"""CAPM Value Strategy implementation."""
import logging
import time
from collections import deque
from datetime import datetime

from src.models import Event, Decision, Action, FundamentalData
from src.strategies.base import Position
from src.strategies.pipeline import StrategyPipeline
from src.strategies.capm_value.layers import (
    UniverseScreen,
    BetaCalculator,
    CAPMValuation,
    CAPMDecision,
)

logger = logging.getLogger(__name__)


class CAPMValueStrategy:
    """CAPM-based value strategy for portfolio allocation.

    This strategy uses the Capital Asset Pricing Model (CAPM) to:
    1. Calculate expected returns based on systematic risk (beta)
    2. Identify mispriced stocks (positive/negative alpha)
    3. Allocate capital to undervalued stocks with positive alpha

    Pipeline layers:
    1. UniverseScreen - Filter for tradeable stocks
    2. BetaCalculator - Calculate stock beta vs market
    3. CAPMValuation - Calculate expected return and alpha
    4. CAPMDecision - Generate trading signals

    Fund allocation: 100,000 SGD
    """

    name = "capm_value"
    subscriptions = ["fundamental_data", "price_bar", "market_bar"]

    def __init__(
        self,
        allocated_capital: float = 100_000.0,
        # Universe screen params
        min_market_cap: float = 500_000_000,
        min_history_days: int = 252,
        excluded_sectors: list[str] | None = None,
        # Beta params
        beta_lookback_days: int = 252,
        min_beta: float = 0.2,
        max_beta: float = 2.5,
        # CAPM params
        risk_free_rate: float = 0.05,
        expected_market_return: float = 0.10,
        # Decision params
        buy_alpha_threshold: float = 0.02,
        exit_alpha_threshold: float = -0.02,
        min_sharpe_for_buy: float = 0.5,
        max_position_weight: float = 0.10,
        # Price history config
        price_history_days: int = 300,
        market_symbol: str = "SPY",
    ):
        """Initialize the CAPM value strategy.

        Args:
            allocated_capital: Capital allocated to this strategy (default: 100k SGD)
            min_market_cap: Minimum market cap for universe (default: 500M)
            min_history_days: Minimum trading history required (default: 252)
            excluded_sectors: Sectors to exclude from universe
            beta_lookback_days: Days to use for beta calculation (default: 252)
            min_beta: Minimum acceptable beta (default: 0.2)
            max_beta: Maximum acceptable beta (default: 2.5)
            risk_free_rate: Annual risk-free rate (default: 5%)
            expected_market_return: Expected annual market return (default: 10%)
            buy_alpha_threshold: Alpha threshold for BUY (default: 2%)
            exit_alpha_threshold: Alpha threshold for EXIT (default: -2%)
            min_sharpe_for_buy: Minimum Sharpe for BUY signals (default: 0.5)
            max_position_weight: Maximum weight per position (default: 10%)
            price_history_days: Days of price history to maintain (default: 300)
            market_symbol: Symbol to use as market benchmark (default: SPY)
        """
        self.allocated_capital = allocated_capital
        self.market_symbol = market_symbol
        self.price_history_days = price_history_days

        logger.debug(
            "INIT: CAPMValueStrategy starting initialization",
            extra={
                "extra_data": {
                    "action": "strategy_init",
                    "strategy": self.name,
                    "allocated_capital": allocated_capital,
                    "market_symbol": market_symbol,
                }
            },
        )

        # Build the layer pipeline
        self.pipeline = StrategyPipeline(
            layers=[
                UniverseScreen(
                    min_market_cap=min_market_cap,
                    min_history_days=min_history_days,
                    excluded_sectors=excluded_sectors or [],
                ),
                BetaCalculator(
                    lookback_days=beta_lookback_days,
                    min_beta=min_beta,
                    max_beta=max_beta,
                ),
                CAPMValuation(
                    risk_free_rate=risk_free_rate,
                    expected_market_return=expected_market_return,
                    use_historical_market_return=True,
                ),
                CAPMDecision(
                    buy_alpha_threshold=buy_alpha_threshold,
                    exit_alpha_threshold=exit_alpha_threshold,
                    min_sharpe_for_buy=min_sharpe_for_buy,
                    max_position_weight=max_position_weight,
                ),
            ]
        )

        # Internal state
        self._positions: dict[str, Position] = {}
        self._fundamentals: dict[str, FundamentalData] = {}
        self._prices: dict[str, float] = {}
        self._price_history: dict[str, deque[float]] = {}
        self._market_history: deque[float] = deque(maxlen=price_history_days)
        self._last_analysis: dict[str, dict] = {}

        logger.info(
            f"CAPMValueStrategy initialized: capital=${allocated_capital:,.0f}, "
            f"market_benchmark={market_symbol}"
        )

        logger.debug(
            "INIT: CAPMValueStrategy initialization complete",
            extra={
                "extra_data": {
                    "action": "strategy_init_complete",
                    "strategy": self.name,
                    "pipeline_layers": [layer.name for layer in self.pipeline.layers],
                    "config": {
                        "min_market_cap": min_market_cap,
                        "min_history_days": min_history_days,
                        "beta_lookback_days": beta_lookback_days,
                        "min_beta": min_beta,
                        "max_beta": max_beta,
                        "risk_free_rate": risk_free_rate,
                        "buy_alpha_threshold": buy_alpha_threshold,
                        "exit_alpha_threshold": exit_alpha_threshold,
                        "min_sharpe_for_buy": min_sharpe_for_buy,
                        "max_position_weight": max_position_weight,
                    },
                }
            },
        )

    def on_event(self, event: Event) -> list[Decision]:
        """Process an event through the strategy pipeline.

        Args:
            event: The event to process

        Returns:
            List of trading decisions (may be empty)
        """
        start_time = time.perf_counter()

        logger.debug(
            f"ENTER: CAPMValueStrategy.on_event",
            extra={
                "extra_data": {
                    "action": "event_received",
                    "strategy": self.name,
                    "event_type": event.type,
                    "symbol": event.symbol,
                    "timestamp": event.timestamp.isoformat(),
                }
            },
        )

        if event.symbol is None:
            return []

        symbol = event.symbol

        # Handle different event types
        if event.type == "market_bar":
            self._handle_market_bar(event)
            return []

        if event.type == "price_bar":
            self._handle_price_bar(symbol, event)

        elif event.type == "fundamental_data":
            self._handle_fundamental_data(symbol, event)

        # Check if we have enough data to run pipeline
        if not self._can_run_pipeline(symbol):
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(
                f"EXIT: CAPMValueStrategy.on_event - insufficient data",
                extra={
                    "extra_data": {
                        "action": "event_skip",
                        "strategy": self.name,
                        "symbol": symbol,
                        "reason": "insufficient_data",
                        "has_fundamental": symbol in self._fundamentals,
                        "has_price": symbol in self._prices,
                        "price_history_len": len(self._price_history.get(symbol, [])),
                        "market_history_len": len(self._market_history),
                        "elapsed_ms": elapsed_ms,
                    }
                },
            )
            return []

        # Build data dict for pipeline
        data = self._build_pipeline_data(symbol)

        logger.debug(
            f"STEP: Running pipeline for {symbol}",
            extra={
                "extra_data": {
                    "action": "pipeline_start",
                    "strategy": self.name,
                    "symbol": symbol,
                    "data_keys": list(data.keys()),
                    "price_history_len": len(data.get("price_history", [])),
                    "market_history_len": len(data.get("market_history", [])),
                }
            },
        )

        # Run through pipeline
        passed, final_data, reasoning = self.pipeline.run(symbol, data)

        # Store analysis results
        self._last_analysis[symbol] = {
            "passed": passed,
            "timestamp": datetime.now().isoformat(),
            "beta": final_data.get("beta"),
            "alpha": final_data.get("alpha"),
            "expected_return": final_data.get("expected_return"),
            "sharpe_ratio": final_data.get("sharpe_ratio"),
        }

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        logger.debug(
            f"EXIT: CAPMValueStrategy.on_event - pipeline complete",
            extra={
                "extra_data": {
                    "action": "pipeline_complete",
                    "strategy": self.name,
                    "symbol": symbol,
                    "passed": passed,
                    "analysis": self._last_analysis[symbol],
                    "elapsed_ms": elapsed_ms,
                }
            },
        )

        logger.info(f"Pipeline result for {symbol}: passed={passed}")
        logger.debug(f"Reasoning:\n{reasoning}")

        # Generate decision if pipeline passed
        if passed:
            action = final_data.get("action", Action.HOLD)
            target_weight = final_data.get("target_weight", 0.0)
            confidence = final_data.get("confidence", 1.0)

            decision = Decision(
                symbol=symbol,
                action=action,
                target_weight=target_weight,
                confidence=confidence,
                reasoning=reasoning,
            )

            logger.info(
                f"CAPM decision for {symbol}: {action.value.upper()} "
                f"(weight={target_weight:.1%}, confidence={confidence:.0%})"
            )

            return [decision]

        return []

    def _handle_market_bar(self, event: Event) -> None:
        """Handle market benchmark price bar.

        Args:
            event: Market bar event
        """
        close_price = event.payload.get("close", 0)
        if close_price > 0:
            self._market_history.append(close_price)

            logger.debug(
                f"TRANSFORM: Market history updated",
                extra={
                    "extra_data": {
                        "action": "market_update",
                        "strategy": self.name,
                        "market_symbol": self.market_symbol,
                        "price": close_price,
                        "history_len": len(self._market_history),
                    }
                },
            )

    def _handle_price_bar(self, symbol: str, event: Event) -> None:
        """Handle stock price bar.

        Args:
            symbol: Stock symbol
            event: Price bar event
        """
        close_price = event.payload.get("close", 0)
        if close_price > 0:
            self._prices[symbol] = close_price

            # Initialize history deque if needed
            if symbol not in self._price_history:
                self._price_history[symbol] = deque(maxlen=self.price_history_days)

            self._price_history[symbol].append(close_price)

            logger.debug(
                f"TRANSFORM: Price history updated for {symbol}",
                extra={
                    "extra_data": {
                        "action": "price_update",
                        "strategy": self.name,
                        "symbol": symbol,
                        "price": close_price,
                        "history_len": len(self._price_history[symbol]),
                    }
                },
            )

    def _handle_fundamental_data(self, symbol: str, event: Event) -> None:
        """Handle fundamental data event.

        Args:
            symbol: Stock symbol
            event: Fundamental data event
        """
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

        logger.debug(
            f"TRANSFORM: Fundamental data stored for {symbol}",
            extra={
                "extra_data": {
                    "action": "fundamental_update",
                    "strategy": self.name,
                    "symbol": symbol,
                    "company_name": payload.get("company_name"),
                    "industry": payload.get("industry"),
                    "shares_outstanding": payload.get("shares_outstanding"),
                }
            },
        )

    def _can_run_pipeline(self, symbol: str) -> bool:
        """Check if we have enough data to run the pipeline.

        Args:
            symbol: Stock symbol

        Returns:
            True if we can run the pipeline
        """
        has_fundamental = symbol in self._fundamentals
        has_price = symbol in self._prices
        has_price_history = (
            symbol in self._price_history and len(self._price_history[symbol]) >= 20
        )
        has_market_history = len(self._market_history) >= 20

        can_run = has_fundamental and has_price and has_price_history and has_market_history

        logger.debug(
            f"DECISION: Pipeline eligibility check for {symbol}",
            extra={
                "extra_data": {
                    "action": "decision_point",
                    "decision": "pipeline_eligibility",
                    "symbol": symbol,
                    "has_fundamental": has_fundamental,
                    "has_price": has_price,
                    "has_price_history": has_price_history,
                    "has_market_history": has_market_history,
                    "can_run": can_run,
                }
            },
        )

        return can_run

    def _build_pipeline_data(self, symbol: str) -> dict:
        """Build data dict for pipeline processing.

        Args:
            symbol: Stock symbol

        Returns:
            Data dict with all required inputs
        """
        data = {
            "fundamental": self._fundamentals[symbol],
            "price": self._prices[symbol],
            "price_history": list(self._price_history[symbol]),
            "market_history": list(self._market_history),
        }

        logger.debug(
            f"TRANSFORM: Pipeline data built for {symbol}",
            extra={
                "extra_data": {
                    "action": "transform_output",
                    "transform": "build_pipeline_data",
                    "symbol": symbol,
                    "price": data["price"],
                    "price_history_len": len(data["price_history"]),
                    "market_history_len": len(data["market_history"]),
                    "fundamental_company": data["fundamental"].company_name,
                }
            },
        )

        return data

    def get_positions(self) -> dict[str, Position]:
        """Get current positions held by this strategy."""
        return self._positions.copy()

    def get_analysis(self, symbol: str) -> dict | None:
        """Get last analysis results for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Analysis dict or None if not analyzed
        """
        return self._last_analysis.get(symbol)

    def get_state(self) -> dict:
        """Get serializable state for persistence."""
        state = {
            "prices": self._prices.copy(),
            "price_history": {
                symbol: list(history)
                for symbol, history in self._price_history.items()
            },
            "market_history": list(self._market_history),
            "last_analysis": self._last_analysis.copy(),
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

        logger.debug(
            "TRANSFORM: State serialized",
            extra={
                "extra_data": {
                    "action": "state_serialize",
                    "strategy": self.name,
                    "symbols_with_prices": len(state["prices"]),
                    "symbols_with_history": len(state["price_history"]),
                    "market_history_len": len(state["market_history"]),
                    "positions_count": len(state["positions"]),
                }
            },
        )

        return state

    def load_state(self, state: dict) -> None:
        """Restore strategy from saved state.

        Args:
            state: Previously saved state dict
        """
        self._prices = state.get("prices", {})

        # Restore price history
        price_history_data = state.get("price_history", {})
        self._price_history = {
            symbol: deque(history, maxlen=self.price_history_days)
            for symbol, history in price_history_data.items()
        }

        # Restore market history
        market_history_data = state.get("market_history", [])
        self._market_history = deque(market_history_data, maxlen=self.price_history_days)

        self._last_analysis = state.get("last_analysis", {})

        # Restore positions
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

        logger.info(
            f"Restored state: {len(self._prices)} prices, "
            f"{len(self._positions)} positions, "
            f"{len(self._market_history)} market history days"
        )

        logger.debug(
            "TRANSFORM: State restored",
            extra={
                "extra_data": {
                    "action": "state_restore",
                    "strategy": self.name,
                    "symbols_with_prices": len(self._prices),
                    "symbols_with_history": len(self._price_history),
                    "market_history_len": len(self._market_history),
                    "positions_count": len(self._positions),
                }
            },
        )
