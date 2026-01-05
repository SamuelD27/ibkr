"""IBKR TWS/Gateway connection manager."""
import logging
import threading
from typing import Callable

logger = logging.getLogger(__name__)


class IBKRConnection:
    """Manages connection to IBKR TWS or Gateway.

    This class handles connection lifecycle, order ID management,
    and provides callback hooks for connection events.

    Attributes:
        host: TWS/Gateway hostname
        port: TWS/Gateway port (7496/7497 for TWS, 4001/4002 for Gateway)
        client_id: Unique client identifier for this connection
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,
        client_id: int = 0,
    ):
        """Initialize connection manager.

        Args:
            host: TWS/Gateway hostname (default: localhost)
            port: TWS/Gateway port (default: 7497 for paper trading)
            client_id: Unique client ID (default: 0)
        """
        self.host = host
        self.port = port
        self.client_id = client_id

        self._connected = False
        self._next_order_id: int | None = None
        self._lock = threading.Lock()

        # Callbacks
        self.on_error: Callable[[int, str], None] | None = None

    def is_connected(self) -> bool:
        """Check if currently connected to TWS/Gateway."""
        return self._connected

    def _set_connected(self, connected: bool) -> None:
        """Set connection status (called internally)."""
        self._connected = connected

    @property
    def next_order_id(self) -> int:
        """Get the next valid order ID, auto-incrementing.

        Raises:
            RuntimeError: If not connected (nextValidId not yet received)
        """
        with self._lock:
            if self._next_order_id is None:
                raise RuntimeError("Cannot get order ID: not connected")

            order_id = self._next_order_id
            self._next_order_id += 1
            return order_id

    def _on_next_valid_id(self, order_id: int) -> None:
        """Handle nextValidId callback from TWS.

        Args:
            order_id: The next valid order ID from TWS
        """
        with self._lock:
            self._next_order_id = order_id
            logger.info(f"Received next valid order ID: {order_id}")

    def _on_error(self, error_code: int, error_message: str) -> None:
        """Handle error callback from TWS.

        Args:
            error_code: IBKR error code
            error_message: Error description
        """
        logger.error(f"IBKR Error {error_code}: {error_message}")

        if self.on_error:
            self.on_error(error_code, error_message)
