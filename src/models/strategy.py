"""Strategy models for IBKR Trading Bot."""
from dataclasses import dataclass
from typing import Any

from src.models.orders import Action


@dataclass
class LayerResult:
    """Result from a strategy layer."""
    passed: bool
    data: dict[str, Any]
    reasoning: str


@dataclass
class Decision:
    """Final decision from a strategy."""
    symbol: str
    action: Action
    target_weight: float  # 0.0 to 1.0
    confidence: float     # 0.0 to 1.0
    reasoning: str        # Full audit trail
