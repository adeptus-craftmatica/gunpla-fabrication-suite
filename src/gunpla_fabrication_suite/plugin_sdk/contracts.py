"""Typed contribution points a plugin can register through :class:`PluginContext`.

More contribution types (settings pages, importers, exporters, reports,
search providers, automation triggers/actions, ...) will be added as the
milestones that consume them are implemented. Adding an unused contribution
type ahead of any consumer is deliberately avoided.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget

WidgetFactory = Callable[[], QWidget]


@dataclass(frozen=True, slots=True)
class NavigationPageContribution:
    """A page a plugin adds to the shell's main or secondary navigation."""

    page_id: str
    title: str
    factory: WidgetFactory
    icon: QIcon | None = None
    section: str = "main"
    order: int = 100
    focus: Callable[[str], None] | None = None
    """Prime this page to show one specific record, given its id.

    Set by a plugin that wants "jump to a specific record" support (e.g.
    from Global Search) — the callable should do whatever the page's own
    ``show_<record>`` method does. Left ``None`` for pages with no
    single-record concept (Dashboard, Plugin Manager, Stats).
    """


@dataclass(frozen=True, slots=True)
class DashboardWidgetContribution:
    """A widget a plugin contributes to the dashboard page."""

    widget_id: str
    title: str
    factory: WidgetFactory
    order: int = 100


@dataclass(frozen=True, slots=True)
class CommandContribution:
    """An action a plugin exposes through the command palette."""

    command_id: str
    title: str
    callback: Callable[[], None]
    shortcut: str | None = None
