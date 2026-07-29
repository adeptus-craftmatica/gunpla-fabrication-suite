"""The object handed to every plugin during registration."""

from __future__ import annotations

from dataclasses import dataclass

import structlog

from gunpla_fabrication_suite.core.events import EventBus
from gunpla_fabrication_suite.core.logging import get_logger
from gunpla_fabrication_suite.core.notifications import NotificationCenter
from gunpla_fabrication_suite.core.paths import ApplicationPaths
from gunpla_fabrication_suite.core.persistence import DatabaseService
from gunpla_fabrication_suite.core.services import ServiceContainer
from gunpla_fabrication_suite.plugin_sdk.registries import (
    CommandRegistry,
    DashboardWidgetRegistry,
    NavigationRegistry,
)


@dataclass(frozen=True, slots=True)
class PluginContext:
    """Everything a plugin needs, handed to it once at registration time.

    A plugin must not reach around this object into
    ``gunpla_fabrication_suite.core`` or ``gunpla_fabrication_suite.shell``
    internals directly.
    """

    plugin_id: str
    services: ServiceContainer
    events: EventBus
    database: DatabaseService
    notifications: NotificationCenter
    paths: ApplicationPaths
    navigation: NavigationRegistry
    dashboard_widgets: DashboardWidgetRegistry
    commands: CommandRegistry

    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """A structured logger pre-bound to this plugin's id."""
        return get_logger(f"plugin.{self.plugin_id}")
