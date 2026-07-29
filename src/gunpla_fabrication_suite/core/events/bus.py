"""A typed, in-process publish/subscribe event bus.

Events are plain immutable objects (conventionally ``@dataclass(frozen=True, slots=True)``).
Handlers are looked up by the exact event type. A handler that raises is
logged and isolated — it never prevents other handlers, or the publisher,
from continuing.
"""

from __future__ import annotations

import asyncio
import inspect
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from gunpla_fabrication_suite.core.logging import get_logger

_logger = get_logger("events")

EventHandler = Callable[[Any], Any]


@dataclass(frozen=True, slots=True)
class Subscription:
    """A handle returned by :meth:`EventBus.subscribe` that can cancel it."""

    _bus: EventBus
    _event_type: type
    _handler: EventHandler

    def unsubscribe(self) -> None:
        """Remove this handler from the bus. Safe to call more than once."""
        self._bus._unsubscribe(self._event_type, self._handler)


class EventBus:
    """Dispatches domain events to subscribed handlers.

    Handlers may be regular callables or ``async def`` coroutine functions.
    Coroutine handlers are scheduled on the running asyncio event loop
    (installed via ``qasync`` alongside the Qt event loop) and are not
    awaited by the publisher.
    """

    def __init__(self) -> None:
        self._handlers: dict[type, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: EventHandler) -> Subscription:
        """Register ``handler`` to be called whenever ``event_type`` is published."""
        self._handlers[event_type].append(handler)
        return Subscription(_bus=self, _event_type=event_type, _handler=handler)

    def _unsubscribe(self, event_type: type, handler: EventHandler) -> None:
        handlers = self._handlers.get(event_type)
        if handlers and handler in handlers:
            handlers.remove(handler)

    def publish(self, event: object) -> None:
        """Dispatch ``event`` to every handler registered for its type.

        Handlers registered for a superclass of ``type(event)`` are not
        invoked — subscriptions are exact-type matches, keeping dispatch
        predictable and event contracts explicit.
        """
        event_type = type(event)
        handlers = list(self._handlers.get(event_type, ()))
        if not handlers:
            return

        for handler in handlers:
            try:
                if inspect.iscoroutinefunction(handler):
                    self._schedule_coroutine(handler, event)
                else:
                    handler(event)
            except Exception:
                _logger.exception(
                    "event_handler_failed",
                    event_type=event_type.__name__,
                    handler=getattr(handler, "__qualname__", repr(handler)),
                )

    def _schedule_coroutine(self, handler: EventHandler, event: object) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            _logger.warning(
                "async_handler_no_event_loop",
                handler=getattr(handler, "__qualname__", repr(handler)),
            )
            return

        task = loop.create_task(handler(event))

        def _log_if_failed(done_task: asyncio.Task[Any]) -> None:
            if done_task.cancelled():
                return
            exc = done_task.exception()
            if exc is not None:
                _logger.error(
                    "async_event_handler_failed",
                    handler=getattr(handler, "__qualname__", repr(handler)),
                    error=str(exc),
                )

        task.add_done_callback(_log_if_failed)
