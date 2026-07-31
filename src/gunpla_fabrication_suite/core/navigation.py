"""A tiny cross-cutting signal for plugins to request a page switch.

Dashboard widgets are constructed lazily by each plugin's own
``DashboardWidgetContribution.factory``, long after the shell exists, with
no reference back to it (see ``PluginContext``, which hands out
infrastructure services but never the shell itself). This gives a plugin a
safe, decoupled way to say "switch the visible page to mine" without
importing anything from ``gunpla_fabrication_suite.shell``.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class Navigator(QObject):
    """Broadcasts requests to switch the shell's visible navigation page."""

    navigate_requested = Signal(str)

    def navigate_to(self, page_id: str) -> None:
        """Request that the shell switch to the page registered under ``page_id``.

        Silently does nothing if ``page_id`` isn't currently registered
        (the same behavior as clicking a navigation rail button that no
        longer exists).
        """
        self.navigate_requested.emit(page_id)
