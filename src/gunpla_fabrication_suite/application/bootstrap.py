"""Application startup sequence.

This is the one place allowed to know about every core subsystem at once.
Nothing here contains Gunpla-domain logic — it constructs infrastructure,
lets the plugin manager discover and load plugins, and hands control to the
Qt event loop.
"""

from __future__ import annotations

import asyncio
import sys
import traceback

import qasync
from PySide6.QtWidgets import QApplication, QMessageBox

from gunpla_fabrication_suite.core.events import EventBus
from gunpla_fabrication_suite.core.jobs import BackgroundJobManager
from gunpla_fabrication_suite.core.logging import configure_logging, get_logger
from gunpla_fabrication_suite.core.notifications import NotificationCenter
from gunpla_fabrication_suite.core.paths import resolve_application_paths
from gunpla_fabrication_suite.core.persistence import DatabaseService
from gunpla_fabrication_suite.core.plugins import PluginManager
from gunpla_fabrication_suite.core.services import ServiceContainer
from gunpla_fabrication_suite.core.settings import SettingsService
from gunpla_fabrication_suite.plugin_sdk.registries import (
    CommandRegistry,
    DashboardWidgetRegistry,
    NavigationRegistry,
)
from gunpla_fabrication_suite.shell.main_window import MainWindow, configure_qsettings_identity
from gunpla_fabrication_suite.themes import apply_dark_theme

_logger = get_logger("startup")


def run_application(argv: list[str] | None = None) -> int:
    """Bootstrap and run the application. Returns the process exit code."""
    paths = resolve_application_paths()
    paths.ensure_exists()
    configure_logging(paths.logs_dir)
    _logger.info("application_starting", data_root=str(paths.root))

    settings_service = SettingsService(paths.settings_file)

    configure_qsettings_identity()
    app = QApplication(argv if argv is not None else sys.argv)
    apply_dark_theme(app)

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    database = DatabaseService(paths.database_file)
    try:
        database.migrate()
    except Exception:
        _logger.exception("database_migration_failed")

    services = ServiceContainer()
    events = EventBus()
    notifications = NotificationCenter()
    jobs = BackgroundJobManager()

    navigation = NavigationRegistry()
    dashboard_widgets = DashboardWidgetRegistry()
    commands = CommandRegistry()

    disabled_plugin_ids = frozenset(settings_service.current.disabled_plugins)
    plugin_manager = PluginManager(
        services=services,
        events=events,
        database=database,
        notifications=notifications,
        paths=paths,
        navigation=navigation,
        dashboard_widgets=dashboard_widgets,
        commands=commands,
        disabled_plugin_ids=disabled_plugin_ids,
    )
    plugin_manager.discover_and_load()

    try:
        window = MainWindow(
            navigation=navigation,
            dashboard_widgets=dashboard_widgets,
            commands=commands,
            plugin_manager=plugin_manager,
            database=database,
            notifications=notifications,
            jobs=jobs,
            paths=paths,
            settings_service=settings_service,
        )
    except Exception as exc:
        _logger.critical("main_window_construction_failed", error=str(exc))
        traceback.print_exc()
        QMessageBox.critical(
            None,
            "Gunpla Fabrication Suite failed to start",
            f"An unexpected error prevented the application from starting:\n\n{exc}\n\n"
            f"See the log file in {paths.logs_dir} for details.",
        )
        database.dispose()
        return 1

    window.show()
    _logger.info("application_started")

    with loop:
        loop.run_forever()

    database.dispose()
    return 0
