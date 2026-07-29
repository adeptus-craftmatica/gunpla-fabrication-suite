"""Typed, validated application settings persisted to a JSON file.

Settings are validated by Pydantic before being written to disk, so a
malformed in-memory value can never be persisted. Plugins that need their own
settings should define their own Pydantic model and store it under
:attr:`ApplicationSettings.plugin_settings`, keyed by plugin id, rather than
extending this core model.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from gunpla_fabrication_suite.core.logging import get_logger

_logger = get_logger("settings")


class GeneralSettings(BaseModel):
    """General/appearance settings shown in the Settings page."""

    theme: str = "dark"
    interface_density: str = "comfortable"
    reduced_motion: bool = False


class ApplicationSettings(BaseModel):
    """The root, persisted settings document."""

    schema_version: int = 1
    general: GeneralSettings = Field(default_factory=GeneralSettings)
    disabled_plugins: list[str] = Field(default_factory=list)
    recent_items: list[str] = Field(default_factory=list)
    plugin_settings: dict[str, dict[str, Any]] = Field(default_factory=dict)


class SettingsService:
    """Loads, validates, and persists :class:`ApplicationSettings`."""

    def __init__(self, settings_file: Path) -> None:
        self._settings_file = settings_file
        self._settings = self._load()

    @property
    def current(self) -> ApplicationSettings:
        """The currently loaded, validated settings document."""
        return self._settings

    def _load(self) -> ApplicationSettings:
        if not self._settings_file.exists():
            return ApplicationSettings()
        try:
            raw = self._settings_file.read_text(encoding="utf-8")
            return ApplicationSettings.model_validate_json(raw)
        except Exception:
            _logger.exception("settings_load_failed", path=str(self._settings_file))
            return ApplicationSettings()

    def save(self, settings: ApplicationSettings | None = None) -> None:
        """Validate and atomically persist ``settings`` (or the current document)."""
        if settings is not None:
            self._settings = settings

        self._settings_file.parent.mkdir(parents=True, exist_ok=True)
        payload = self._settings.model_dump_json(indent=2)

        tmp_path = self._settings_file.with_suffix(".tmp")
        tmp_path.write_text(payload, encoding="utf-8")
        tmp_path.replace(self._settings_file)

    def reset_to_defaults(self) -> None:
        """Discard all settings and persist a fresh default document."""
        self._settings = ApplicationSettings()
        self.save()
