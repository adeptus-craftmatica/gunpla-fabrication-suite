"""Discovers, resolves, loads, and manages the lifecycle of every plugin.

A failing plugin is isolated: it is marked unhealthy, a notification is
posted, and every other plugin continues loading. Nothing here ever lets one
plugin's exception propagate out and crash application startup.
"""

from __future__ import annotations

import importlib

from gunpla_fabrication_suite.core.events import EventBus
from gunpla_fabrication_suite.core.jobs import BackgroundJobManager
from gunpla_fabrication_suite.core.layout import LayoutManager
from gunpla_fabrication_suite.core.logging import get_logger
from gunpla_fabrication_suite.core.navigation import Navigator
from gunpla_fabrication_suite.core.notifications import NotificationCenter, NotificationSeverity
from gunpla_fabrication_suite.core.paths import ApplicationPaths
from gunpla_fabrication_suite.core.persistence import DatabaseService
from gunpla_fabrication_suite.core.plugins.discovery import (
    DiscoveredPlugin,
    discover_all_plugins,
)
from gunpla_fabrication_suite.core.plugins.records import PluginHealth, PluginRecord, PluginStatus
from gunpla_fabrication_suite.core.services import ServiceContainer
from gunpla_fabrication_suite.core.theming import ThemeManager
from gunpla_fabrication_suite.plugin_sdk.context import PluginContext
from gunpla_fabrication_suite.plugin_sdk.interface import PluginInterface
from gunpla_fabrication_suite.plugin_sdk.registries import (
    CommandRegistry,
    DashboardWidgetRegistry,
    NavigationRegistry,
)
from gunpla_fabrication_suite.shared_ui import InspectorPanel

_logger = get_logger("plugins")


class PluginDependencyError(RuntimeError):
    """Raised internally when a plugin's dependencies cannot be satisfied."""


class PluginManager:
    """Owns the full plugin lifecycle: discovery, loading, and shutdown."""

    def __init__(
        self,
        *,
        services: ServiceContainer,
        events: EventBus,
        database: DatabaseService,
        notifications: NotificationCenter,
        jobs: BackgroundJobManager,
        navigator: Navigator,
        theme_manager: ThemeManager,
        layout_manager: LayoutManager,
        inspector: InspectorPanel,
        paths: ApplicationPaths,
        navigation: NavigationRegistry,
        dashboard_widgets: DashboardWidgetRegistry,
        commands: CommandRegistry,
        disabled_plugin_ids: frozenset[str] = frozenset(),
    ) -> None:
        self._services = services
        self._events = events
        self._database = database
        self._notifications = notifications
        self._jobs = jobs
        self._navigator = navigator
        self._theme_manager = theme_manager
        self._layout_manager = layout_manager
        self._inspector = inspector
        self._paths = paths
        self._navigation = navigation
        self._dashboard_widgets = dashboard_widgets
        self._commands = commands
        self._disabled_plugin_ids = disabled_plugin_ids
        self._records: dict[str, PluginRecord] = {}

    @property
    def records(self) -> tuple[PluginRecord, ...]:
        """Every discovered plugin's current record, in load order."""
        return tuple(self._records.values())

    def get(self, plugin_id: str) -> PluginRecord | None:
        """Look up a plugin's record by id."""
        return self._records.get(plugin_id)

    def discover_and_load(self) -> None:
        """Discover every plugin and load those whose dependencies are satisfied."""
        discovered = discover_all_plugins(self._paths.plugins_dir)
        for plugin in discovered:
            self._records[plugin.manifest.id] = PluginRecord(
                manifest=plugin.manifest, source=plugin.source
            )

        for plugin in self._resolve_load_order(discovered):
            record = self._records[plugin.manifest.id]

            if plugin.manifest.id in self._disabled_plugin_ids:
                record.status = PluginStatus.DISABLED
                continue

            missing = [
                dep
                for dep in plugin.manifest.dependencies
                if not self._records.get(dep) or self._records[dep].status != PluginStatus.STARTED
            ]
            if missing:
                self._fail(record, f"Missing or unhealthy dependencies: {', '.join(missing)}")
                continue

            self._load_one(plugin, record)

    def _resolve_load_order(self, discovered: list[DiscoveredPlugin]) -> list[DiscoveredPlugin]:
        """Topologically sort plugins so dependencies load before dependents."""
        by_id = {plugin.manifest.id: plugin for plugin in discovered}
        ordered: list[DiscoveredPlugin] = []
        visited: set[str] = set()
        visiting: set[str] = set()

        def visit(plugin_id: str) -> None:
            if plugin_id in visited or plugin_id not in by_id:
                return
            if plugin_id in visiting:
                _logger.error("plugin_dependency_cycle", plugin_id=plugin_id)
                return
            visiting.add(plugin_id)
            for dep in by_id[plugin_id].manifest.dependencies:
                visit(dep)
            visiting.discard(plugin_id)
            visited.add(plugin_id)
            ordered.append(by_id[plugin_id])

        for plugin in discovered:
            visit(plugin.manifest.id)
        return ordered

    def _load_one(self, plugin: DiscoveredPlugin, record: PluginRecord) -> None:
        plugin_id = plugin.manifest.id
        try:
            module = importlib.import_module(plugin.module_name)
            plugin_class = getattr(module, plugin.class_name)
            instance: PluginInterface = plugin_class()
        except Exception as exc:
            self._fail(record, f"Failed to import or instantiate plugin: {exc}")
            return

        record.instance = instance
        context = PluginContext(
            plugin_id=plugin_id,
            services=self._services,
            events=self._events,
            database=self._database,
            notifications=self._notifications,
            jobs=self._jobs,
            navigator=self._navigator,
            theme_manager=self._theme_manager,
            layout_manager=self._layout_manager,
            inspector=self._inspector,
            paths=self._paths,
            navigation=self._navigation,
            dashboard_widgets=self._dashboard_widgets,
            commands=self._commands,
        )

        for step_name, step in (
            ("register", lambda: instance.register(context)),
            ("initialize", instance.initialize),
            ("start", instance.start),
        ):
            try:
                step()
            except Exception as exc:
                self._fail(record, f"Plugin {step_name} failed: {exc}")
                _logger.exception(
                    "plugin_lifecycle_step_failed", plugin_id=plugin_id, step=step_name
                )
                self._navigation.unregister_all_for(plugin_id)
                self._dashboard_widgets.unregister_all_for(plugin_id)
                self._commands.unregister_all_for(plugin_id)
                return

        record.status = PluginStatus.STARTED
        record.health = PluginHealth.HEALTHY
        _logger.info("plugin_started", plugin_id=plugin_id, source=plugin.source)

    def _fail(self, record: PluginRecord, message: str) -> None:
        record.status = PluginStatus.FAILED
        record.health = PluginHealth.UNHEALTHY
        record.error = message
        _logger.error("plugin_failed", plugin_id=record.manifest.id, error=message)
        self._notifications.post(
            f"Plugin '{record.manifest.name}' failed to load: {message}",
            severity=NotificationSeverity.WARNING,
            source="plugin_manager",
        )

    def shutdown_all(self) -> None:
        """Stop and shut down every started plugin, most-recently-started first."""
        for record in reversed(self._records.values()):
            if record.instance is None or record.status != PluginStatus.STARTED:
                continue
            steps = (("stop", record.instance.stop), ("shutdown", record.instance.shutdown))
            for step_name, step in steps:
                try:
                    step()
                except Exception:
                    _logger.exception(
                        "plugin_shutdown_step_failed",
                        plugin_id=record.manifest.id,
                        step=step_name,
                    )
            record.status = PluginStatus.STOPPED
