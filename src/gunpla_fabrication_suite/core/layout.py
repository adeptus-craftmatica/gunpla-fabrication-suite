"""Live layout switching: holds the active shell/page layout id and persists the choice.

Unlike :class:`~gunpla_fabrication_suite.core.theming.ThemeManager`, this
manager doesn't "apply" anything itself — a layout has no data bundle to
push onto a `QApplication`. Consumers (the shell, individual pages) read
:attr:`LayoutManager.current` at their own construction time, and subscribe
to :attr:`layout_changed` to re-compose themselves in place afterward.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from gunpla_fabrication_suite.core.logging import get_logger
from gunpla_fabrication_suite.core.settings import SettingsService

_logger = get_logger("layout")

RAIL = "rail"
COMMAND_DECK = "command_deck"
WORKBENCH = "workbench"
DIORAMA = "diorama"

LAYOUTS: dict[str, str] = {
    RAIL: "Rail",
    COMMAND_DECK: "Command Deck",
    WORKBENCH: "Workbench",
    DIORAMA: "Diorama",
}
DEFAULT_LAYOUT = RAIL


class LayoutManager(QObject):
    """Owns the active layout id, notifies subscribers, and persists the choice."""

    layout_changed = Signal(str)

    def __init__(self, settings_service: SettingsService) -> None:
        super().__init__()
        self._settings_service = settings_service

        requested_id = settings_service.current.general.layout
        if requested_id not in LAYOUTS:
            _logger.warning("unknown_layout_id_falling_back", requested=requested_id)
            requested_id = DEFAULT_LAYOUT

        self._current = requested_id

    @property
    def current(self) -> str:
        """The currently active layout id."""
        return self._current

    def available_layouts(self) -> tuple[tuple[str, str], ...]:
        """Every known ``(layout_id, display_name)`` pair, in registration order."""
        return tuple(LAYOUTS.items())

    def set_layout(self, layout_id: str) -> None:
        """Switch to ``layout_id``, live, and persist the choice.

        Does nothing if ``layout_id`` isn't known, or is already active.
        """
        if layout_id not in LAYOUTS or layout_id == self._current:
            return

        self._current = layout_id
        self.layout_changed.emit(layout_id)

        settings = self._settings_service.current
        settings.general.layout = layout_id
        self._settings_service.save(settings)
