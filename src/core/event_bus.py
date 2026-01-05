"""Event bus for routing events to subscribers."""
import logging
import threading
from collections import defaultdict
from typing import Callable

from src.models import Event

logger = logging.getLogger(__name__)


class EventBus:
    """Thread-safe pub/sub event bus for routing events to strategies."""

    def __init__(self):
        self._subscribers: dict[str, list[Callable[[Event], None]]] = defaultdict(list)
        self._lock = threading.Lock()

    def subscribe(self, event_types: list[str], callback: Callable[[Event], None]) -> None:
        """Register callback for specific event types.

        Args:
            event_types: List of event types to subscribe to. Use ["*"] for all events.
            callback: Function to call when matching event is published.
        """
        with self._lock:
            for event_type in event_types:
                self._subscribers[event_type].append(callback)
                logger.debug(f"Subscribed {callback.__name__} to {event_type}")

    def unsubscribe(self, callback: Callable[[Event], None]) -> None:
        """Remove callback from all subscriptions.

        Args:
            callback: The callback function to remove.
        """
        with self._lock:
            for event_type in list(self._subscribers.keys()):
                if callback in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(callback)
                    logger.debug(f"Unsubscribed {callback.__name__} from {event_type}")

    def publish(self, event: Event) -> None:
        """Send event to all subscribers of its type.

        Args:
            event: The event to publish.
        """
        with self._lock:
            # Get specific type subscribers + wildcard subscribers
            callbacks = list(
                self._subscribers.get(event.type, []) +
                self._subscribers.get("*", [])
            )

        for callback in callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in subscriber {callback.__name__}: {e}")
