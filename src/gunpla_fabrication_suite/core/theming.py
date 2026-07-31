"""Live theme switching: applies a theme to the app and persists the choice."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from gunpla_fabrication_suite.core.logging import get_logger
from gunpla_fabrication_suite.core.settings import SettingsService
from gunpla_fabrication_suite.themes import DEFAULT_THEME, THEMES, Theme, apply_theme

_logger = get_logger("theming")


class ThemeManager(QObject):
    """Owns the active theme, applies it to the app, and persists the choice."""

    theme_changed = Signal(Theme)

    def __init__(self, app: QApplication, settings_service: SettingsService) -> None:
        super().__init__()
        self._app = app
        self._settings_service = settings_service

        requested_id = settings_service.current.general.theme
        theme = THEMES.get(requested_id)
        if theme is None:
            _logger.warning("unknown_theme_id_falling_back", requested=requested_id)
            theme = DEFAULT_THEME

        self._current = theme
        apply_theme(app, theme)

    @property
    def current(self) -> Theme:
        """The currently active theme."""
        return self._current

    def available_themes(self) -> tuple[Theme, ...]:
        """Every built-in theme, in registration order."""
        return tuple(THEMES.values())

    def set_theme(self, theme_id: str) -> None:
        """Switch to the theme registered under ``theme_id``, live, and persist the choice.

        Does nothing if ``theme_id`` isn't a registered theme, or is already active.
        """
        theme = THEMES.get(theme_id)
        if theme is None or theme is self._current:
            return

        self._current = theme
        apply_theme(self._app, theme)
        self.theme_changed.emit(theme)

        settings = self._settings_service.current
        settings.general.theme = theme_id
        self._settings_service.save(settings)
