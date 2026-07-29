"""Plugin discovery, dependency resolution, and lifecycle management."""

from __future__ import annotations

from gunpla_fabrication_suite.core.plugins.manager import PluginManager
from gunpla_fabrication_suite.core.plugins.records import (
    PluginHealth,
    PluginRecord,
    PluginStatus,
)

__all__ = ["PluginHealth", "PluginManager", "PluginRecord", "PluginStatus"]
