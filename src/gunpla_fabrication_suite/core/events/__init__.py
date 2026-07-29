"""The application event bus.

Plugins communicate through typed, immutable domain events rather than by
calling into each other's internals. See :mod:`gunpla_fabrication_suite.core.events.bus`.
"""

from __future__ import annotations

from gunpla_fabrication_suite.core.events.bus import EventBus, Subscription

__all__ = ["EventBus", "Subscription"]
