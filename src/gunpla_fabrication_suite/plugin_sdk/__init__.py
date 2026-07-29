"""The public surface plugin authors build against.

Nothing in ``gunpla_fabrication_suite.plugins`` should import from
``gunpla_fabrication_suite.core`` or ``gunpla_fabrication_suite.shell``
directly — everything a plugin needs (service access, event publishing,
navigation/dashboard/command registration, logging) is exposed here through
:class:`PluginContext`.
"""

from __future__ import annotations

from gunpla_fabrication_suite.plugin_sdk.context import PluginContext
from gunpla_fabrication_suite.plugin_sdk.contracts import (
    CommandContribution,
    DashboardWidgetContribution,
    NavigationPageContribution,
)
from gunpla_fabrication_suite.plugin_sdk.interface import PluginInterface
from gunpla_fabrication_suite.plugin_sdk.manifest import PluginManifest, load_manifest
from gunpla_fabrication_suite.plugin_sdk.registries import (
    CommandRegistry,
    DashboardWidgetRegistry,
    NavigationRegistry,
)

__all__ = [
    "CommandContribution",
    "CommandRegistry",
    "DashboardWidgetContribution",
    "DashboardWidgetRegistry",
    "NavigationPageContribution",
    "NavigationRegistry",
    "PluginContext",
    "PluginInterface",
    "PluginManifest",
    "load_manifest",
]
