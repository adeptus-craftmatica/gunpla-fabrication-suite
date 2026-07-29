"""Tests for the event bus: dispatch, isolation, and unsubscription."""

from __future__ import annotations

from dataclasses import dataclass

from gunpla_fabrication_suite.core.events import EventBus


@dataclass(frozen=True, slots=True)
class _SampleEvent:
    value: int


def test_publish_calls_subscribed_handler(event_bus: EventBus) -> None:
    received: list[int] = []
    event_bus.subscribe(_SampleEvent, lambda event: received.append(event.value))

    event_bus.publish(_SampleEvent(value=42))

    assert received == [42]


def test_publish_calls_multiple_handlers_in_registration_order(event_bus: EventBus) -> None:
    order: list[str] = []
    event_bus.subscribe(_SampleEvent, lambda _e: order.append("first"))
    event_bus.subscribe(_SampleEvent, lambda _e: order.append("second"))

    event_bus.publish(_SampleEvent(value=1))

    assert order == ["first", "second"]


def test_publish_ignores_unrelated_event_types(event_bus: EventBus) -> None:
    received: list[int] = []
    event_bus.subscribe(_SampleEvent, lambda event: received.append(event.value))

    event_bus.publish(object())

    assert received == []


def test_handler_exception_is_isolated_from_other_handlers(event_bus: EventBus) -> None:
    received: list[str] = []

    def failing_handler(_event: _SampleEvent) -> None:
        raise RuntimeError("boom")

    event_bus.subscribe(_SampleEvent, failing_handler)
    event_bus.subscribe(_SampleEvent, lambda _e: received.append("survived"))

    event_bus.publish(_SampleEvent(value=1))

    assert received == ["survived"]


def test_unsubscribe_stops_future_dispatch(event_bus: EventBus) -> None:
    received: list[int] = []
    subscription = event_bus.subscribe(_SampleEvent, lambda event: received.append(event.value))

    subscription.unsubscribe()
    event_bus.publish(_SampleEvent(value=1))

    assert received == []


def test_unsubscribe_is_idempotent(event_bus: EventBus) -> None:
    subscription = event_bus.subscribe(_SampleEvent, lambda _e: None)
    subscription.unsubscribe()
    subscription.unsubscribe()  # must not raise
