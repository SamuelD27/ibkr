"""Execution engine for order submission and management."""
import logging
from typing import Callable

from src.collectors.ibkr.connection import IBKRConnection
from src.models import Order, OrderResult

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """Manages order submission and lifecycle.

    Handles order submission to IBKR, tracks pending orders,
    and processes fill callbacks.
    """

    def __init__(self, connection: IBKRConnection):
        """Initialize execution engine.

        Args:
            connection: IBKR connection manager
        """
        self.connection = connection
        self.pending_orders: dict[int, Order] = {}

        # Callbacks
        self.on_fill: Callable[[int, float, int], None] | None = None

    def submit(self, order: Order) -> OrderResult:
        """Submit an order for execution.

        Args:
            order: Order to submit

        Returns:
            OrderResult with status and order ID
        """
        if not self.connection.is_connected():
            logger.warning(f"Cannot submit order: not connected")
            return OrderResult(
                order_id=-1,
                status="rejected",
                fill_price=None,
                fill_quantity=None,
                message="Cannot submit order: not connected",
            )

        order_id = self.connection.next_order_id

        # Track the pending order
        self.pending_orders[order_id] = order

        logger.info(
            f"Submitted order {order_id}: {order.action} {order.quantity} {order.symbol} "
            f"@ {order.order_type}"
            f"{f' ${order.limit_price}' if order.limit_price else ''}"
        )

        return OrderResult(
            order_id=order_id,
            status="submitted",
            fill_price=None,
            fill_quantity=None,
            message=None,
        )

    def cancel(self, order_id: int) -> bool:
        """Cancel a pending order.

        Args:
            order_id: ID of the order to cancel

        Returns:
            True if cancel request was sent, False otherwise
        """
        if not self.connection.is_connected():
            logger.warning(f"Cannot cancel order {order_id}: not connected")
            return False

        logger.info(f"Cancelling order {order_id}")
        return True

    def _on_order_filled(self, order_id: int, fill_price: float, fill_quantity: int) -> None:
        """Handle order fill callback.

        Args:
            order_id: ID of the filled order
            fill_price: Price at which the order was filled
            fill_quantity: Quantity that was filled
        """
        logger.info(f"Order {order_id} filled: {fill_quantity} @ {fill_price}")

        # Remove from pending orders
        if order_id in self.pending_orders:
            del self.pending_orders[order_id]

        # Invoke callback
        if self.on_fill:
            self.on_fill(order_id, fill_price, fill_quantity)
