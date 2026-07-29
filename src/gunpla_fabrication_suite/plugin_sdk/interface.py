"""The plugin lifecycle protocol every plugin entry point must satisfy."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from gunpla_fabrication_suite.plugin_sdk.context import PluginContext


@runtime_checkable
class PluginInterface(Protocol):
    """The lifecycle contract implemented by every plugin's entry-point class.

    Lifecycle order: ``register`` -> ``initialize`` -> ``start``, and on
    shutdown, ``stop`` -> ``shutdown``. ``register`` should only wire up
    contributions (navigation, dashboard widgets, commands); it must not do
    I/O. ``initialize`` may set up repositories/services. ``start`` may begin
    background work such as subscribing to events.
    """

    plugin_id: str

    def register(self, context: PluginContext) -> None:
        """Register navigation, dashboard, and command contributions."""
        ...

    def initialize(self) -> None:
        """Construct repositories, services, and any other internal state."""
        ...

    def start(self) -> None:
        """Begin normal operation, e.g. subscribing to events."""
        ...

    def stop(self) -> None:
        """Stop background activity while keeping state intact for a restart."""
        ...

    def shutdown(self) -> None:
        """Release all resources; the plugin will not be started again."""
        ...
