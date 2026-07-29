"""Runtime status tracking for discovered and loaded plugins."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from gunpla_fabrication_suite.plugin_sdk.interface import PluginInterface
from gunpla_fabrication_suite.plugin_sdk.manifest import PluginManifest


class PluginStatus(StrEnum):
    """Where a plugin is in its lifecycle."""

    DISCOVERED = "discovered"
    REGISTERED = "registered"
    INITIALIZED = "initialized"
    STARTED = "started"
    STOPPED = "stopped"
    DISABLED = "disabled"
    FAILED = "failed"


class PluginHealth(StrEnum):
    """A coarse health signal shown in the Plugin Manager."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class PluginRecord:
    """Everything the Plugin Manager page needs to display about one plugin."""

    manifest: PluginManifest
    source: str
    status: PluginStatus = PluginStatus.DISCOVERED
    health: PluginHealth = PluginHealth.UNKNOWN
    error: str | None = None
    instance: PluginInterface | None = field(default=None, repr=False)

    @property
    def is_enabled(self) -> bool:
        """Whether the plugin successfully reached the STARTED state."""
        return self.status == PluginStatus.STARTED
