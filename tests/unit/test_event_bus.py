"""Tests for EventBus."""
from datetime import datetime
import threading
import pytest


def test_subscribe_and_publish():
    from src.core.event_bus import EventBus
    from src.models import Event

    bus = EventBus()
    received = []

    def handler(event: Event):
        received.append(event)

    bus.subscribe(["price_bar"], handler)

    event = Event(
        type="price_bar",
        symbol="AAPL",
        timestamp=datetime(2026, 1, 5),
        ingested_at=datetime(2026, 1, 5),
        source="test",
        payload={}
    )

    bus.publish(event)

    assert len(received) == 1
    assert received[0].symbol == "AAPL"


def test_subscriber_not_called_for_other_types():
    from src.core.event_bus import EventBus
    from src.models import Event

    bus = EventBus()
    received = []

    def handler(event: Event):
        received.append(event)

    bus.subscribe(["price_bar"], handler)

    event = Event(
        type="fundamental_data",
        symbol="AAPL",
        timestamp=datetime(2026, 1, 5),
        ingested_at=datetime(2026, 1, 5),
        source="test",
        payload={}
    )

    bus.publish(event)

    assert len(received) == 0


def test_multiple_subscribers():
    from src.core.event_bus import EventBus
    from src.models import Event

    bus = EventBus()
    received_a = []
    received_b = []

    bus.subscribe(["price_bar"], lambda e: received_a.append(e))
    bus.subscribe(["price_bar"], lambda e: received_b.append(e))

    event = Event(
        type="price_bar",
        symbol="AAPL",
        timestamp=datetime(2026, 1, 5),
        ingested_at=datetime(2026, 1, 5),
        source="test",
        payload={}
    )

    bus.publish(event)

    assert len(received_a) == 1
    assert len(received_b) == 1


def test_unsubscribe():
    from src.core.event_bus import EventBus
    from src.models import Event

    bus = EventBus()
    received = []

    def handler(event: Event):
        received.append(event)

    bus.subscribe(["price_bar"], handler)
    bus.unsubscribe(handler)

    event = Event(
        type="price_bar",
        symbol="AAPL",
        timestamp=datetime(2026, 1, 5),
        ingested_at=datetime(2026, 1, 5),
        source="test",
        payload={}
    )

    bus.publish(event)

    assert len(received) == 0


def test_wildcard_subscription():
    from src.core.event_bus import EventBus
    from src.models import Event

    bus = EventBus()
    received = []

    bus.subscribe(["*"], lambda e: received.append(e))

    bus.publish(Event(
        type="price_bar",
        symbol="AAPL",
        timestamp=datetime(2026, 1, 5),
        ingested_at=datetime(2026, 1, 5),
        source="test",
        payload={}
    ))

    bus.publish(Event(
        type="fundamental_data",
        symbol="AAPL",
        timestamp=datetime(2026, 1, 5),
        ingested_at=datetime(2026, 1, 5),
        source="test",
        payload={}
    ))

    assert len(received) == 2


def test_thread_safe_publish():
    from src.core.event_bus import EventBus
    from src.models import Event

    bus = EventBus()
    received = []
    lock = threading.Lock()

    def handler(event: Event):
        with lock:
            received.append(event)

    bus.subscribe(["price_bar"], handler)

    def publish_events():
        for i in range(100):
            bus.publish(Event(
                type="price_bar",
                symbol=f"SYM{i}",
                timestamp=datetime(2026, 1, 5),
                ingested_at=datetime(2026, 1, 5),
                source="test",
                payload={"i": i}
            ))

    threads = [threading.Thread(target=publish_events) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(received) == 500


def test_subscriber_error_does_not_stop_others():
    from src.core.event_bus import EventBus
    from src.models import Event

    bus = EventBus()
    received = []

    def failing_handler(event: Event):
        raise ValueError("Test error")

    def good_handler(event: Event):
        received.append(event)

    bus.subscribe(["price_bar"], failing_handler)
    bus.subscribe(["price_bar"], good_handler)

    event = Event(
        type="price_bar",
        symbol="AAPL",
        timestamp=datetime(2026, 1, 5),
        ingested_at=datetime(2026, 1, 5),
        source="test",
        payload={}
    )

    bus.publish(event)

    assert len(received) == 1
