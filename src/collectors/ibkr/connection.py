"""IBKR TWS/Gateway connection manager using ib_async."""
import asyncio
import logging
import time
from typing import Callable

from ib_async import IB, Contract, Stock, util

logger = logging.getLogger(__name__)


class IBKRConnection:
    """Manages connection to IBKR TWS or Gateway using ib_async.

    This class handles connection lifecycle, reconnection logic,
    and provides access to the underlying IB client.

    Attributes:
        host: TWS/Gateway hostname
        port: TWS/Gateway port (7496/7497 for TWS, 4001/4002 for Gateway)
        client_id: Unique client identifier for this connection
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,
        client_id: int = 1,
        readonly: bool = False,
    ):
        """Initialize connection manager.

        Args:
            host: TWS/Gateway hostname (default: localhost)
            port: TWS/Gateway port (default: 7497 for paper trading)
            client_id: Unique client ID (default: 1)
            readonly: If True, connect in readonly mode (no orders)
        """
        self.host = host
        self.port = port
        self.client_id = client_id
        self.readonly = readonly

        self._ib = IB()
        self._reconnect_delay = 5
        self._max_reconnect_delay = 60

        # Callbacks
        self.on_error: Callable[[int, str], None] | None = None
        self.on_connected: Callable[[], None] | None = None
        self.on_disconnected: Callable[[], None] | None = None

        # Wire up IB events
        self._ib.errorEvent += self._on_error
        self._ib.connectedEvent += self._on_connected_event
        self._ib.disconnectedEvent += self._on_disconnected_event

        logger.debug(
            "INIT: IBKRConnection initialized",
            extra={
                "extra_data": {
                    "action": "connection_init",
                    "host": host,
                    "port": port,
                    "client_id": client_id,
                    "readonly": readonly,
                }
            },
        )

    @property
    def ib(self) -> IB:
        """Get the underlying IB client."""
        return self._ib

    def is_connected(self) -> bool:
        """Check if currently connected to TWS/Gateway."""
        return self._ib.isConnected()

    async def connect(self, timeout: float = 10.0) -> bool:
        """Connect to TWS/Gateway.

        Args:
            timeout: Connection timeout in seconds

        Returns:
            True if connected successfully
        """
        logger.info(f"Connecting to IBKR at {self.host}:{self.port}...")

        logger.debug(
            "STEP 1/2: Initiating connection",
            extra={
                "extra_data": {
                    "action": "connect_start",
                    "host": self.host,
                    "port": self.port,
                    "client_id": self.client_id,
                    "timeout": timeout,
                }
            },
        )

        try:
            await self._ib.connectAsync(
                host=self.host,
                port=self.port,
                clientId=self.client_id,
                readonly=self.readonly,
                timeout=timeout,
            )

            logger.debug(
                "STEP 2/2: Connection established",
                extra={
                    "extra_data": {
                        "action": "connect_success",
                        "is_connected": self._ib.isConnected(),
                    }
                },
            )

            logger.info(f"Connected to IBKR (client_id={self.client_id})")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to IBKR: {e}")
            logger.debug(
                "STEP 2/2: Connection failed",
                extra={
                    "extra_data": {
                        "action": "connect_failed",
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                },
            )
            return False

    async def disconnect(self) -> None:
        """Disconnect from TWS/Gateway."""
        logger.info("Disconnecting from IBKR...")
        self._ib.disconnect()
        logger.info("Disconnected from IBKR")

    async def reconnect(self) -> bool:
        """Attempt to reconnect with exponential backoff.

        Returns:
            True if reconnected successfully
        """
        delay = self._reconnect_delay

        while True:
            logger.info(f"Attempting to reconnect in {delay}s...")
            await asyncio.sleep(delay)

            if await self.connect():
                self._reconnect_delay = 5  # Reset delay on success
                return True

            delay = min(delay * 2, self._max_reconnect_delay)

    def _on_error(self, reqId: int, errorCode: int, errorString: str, contract: Contract | None) -> None:
        """Handle error callback from TWS."""
        # Filter out non-error messages
        # 2100-2199: Informational messages (data farm status, etc.)
        # Codes < 1000 are usually informational
        if errorCode < 1000 or (2100 <= errorCode < 2200):
            logger.debug(f"IBKR Info {errorCode}: {errorString}")
            return

        logger.error(f"IBKR Error {errorCode}: {errorString} (reqId={reqId})")

        logger.debug(
            "ERROR: IBKR error received",
            extra={
                "extra_data": {
                    "action": "ibkr_error",
                    "req_id": reqId,
                    "error_code": errorCode,
                    "error_string": errorString,
                    "contract": str(contract) if contract else None,
                }
            },
        )

        if self.on_error:
            self.on_error(errorCode, errorString)

    def _on_connected_event(self) -> None:
        """Handle connected event."""
        logger.info("IBKR connection established")
        if self.on_connected:
            self.on_connected()

    def _on_disconnected_event(self) -> None:
        """Handle disconnected event."""
        logger.warning("IBKR connection lost")
        if self.on_disconnected:
            self.on_disconnected()

    @property
    def next_order_id(self) -> int:
        """Get the next valid order ID.

        Returns:
            Next order ID from TWS
        """
        if not self.is_connected():
            raise RuntimeError("Cannot get order ID: not connected")
        return self._ib.client.getReqId()

    def make_stock_contract(self, symbol: str, exchange: str = "SMART", currency: str = "USD") -> Stock:
        """Create a stock contract.

        Args:
            symbol: Stock symbol
            exchange: Exchange (default: SMART)
            currency: Currency (default: USD)

        Returns:
            Stock contract
        """
        return Stock(symbol, exchange, currency)
