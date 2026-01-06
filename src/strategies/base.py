"""Base protocols and classes for trading strategies."""
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from src.models import Event, Decision, LayerResult


@dataclass
class Position:
    """Represents a position held by a strategy."""

    symbol: str
    quantity: int
    avg_cost: float
    current_price: float

    @property
    def market_value(self) -> float:
        """Calculate current market value."""
        return self.quantity * self.current_price

    @property
    def unrealized_pnl(self) -> float:
        """Calculate unrealized profit/loss."""
        return self.quantity * (self.current_price - self.avg_cost)


@runtime_checkable
class StrategyLayer(Protocol):
    """Protocol for a single layer in a strategy pipeline.

    Layers analyze data and decide whether to pass to the next layer.
    Each layer can enrich the data dict with its analysis results.
    """

    name: str

    def process(self, symbol: str, data: dict) -> LayerResult:
        """Process data through this layer.

        Args:
            symbol: The symbol being analyzed
            data: Dict of data accumulated from previous layers

        Returns:
            LayerResult indicating if processing should continue
        """
        ...


@runtime_checkable
class Strategy(Protocol):
    """Protocol for a multi-layer strategy pipeline.

    Strategies process events through their layer pipeline
    and produce trading decisions.
    """

    name: str
    subscriptions: list[str]  # Event types to subscribe to
    allocated_capital: float

    def on_event(self, event: Event) -> list[Decision]:
        """Process an event through the strategy pipeline.

        Args:
            event: The event to process

        Returns:
            List of trading decisions (may be empty)
        """
        ...

    def get_positions(self) -> dict[str, Position]:
        """Get current positions held by this strategy.

        Returns:
            Dict mapping symbol to Position
        """
        ...

    def get_state(self) -> dict:
        """Get serializable state for persistence.

        Returns:
            Dict that can be JSON serialized
        """
        ...

    def load_state(self, state: dict) -> None:
        """Restore strategy from saved state.

        Args:
            state: Previously saved state dict
        """
        ...
