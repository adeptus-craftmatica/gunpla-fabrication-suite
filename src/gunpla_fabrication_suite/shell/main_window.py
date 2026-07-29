"""The main window: composes navigation, workspace, inspector, and status bar.

This module only wires widgets together; it must not contain business logic.
Each piece it composes (navigation rail, workspace stack, inspector,
status bar, plugin manager page, diagnostics dialog) lives in its own module.
"""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QSettings
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QSplitter

from gunpla_fabrication_suite import __version__
from gunpla_fabrication_suite.core.jobs import BackgroundJobManager
from gunpla_fabrication_suite.core.notifications import NotificationCenter
from gunpla_fabrication_suite.core.paths import ApplicationPaths
from gunpla_fabrication_suite.core.persistence import DatabaseService
from gunpla_fabrication_suite.core.plugins import PluginManager
from gunpla_fabrication_suite.core.settings import SettingsService
from gunpla_fabrication_suite.plugin_sdk.contracts import (
    CommandContribution,
    NavigationPageContribution,
)
from gunpla_fabrication_suite.plugin_sdk.registries import (
    CommandRegistry,
    DashboardWidgetRegistry,
    NavigationRegistry,
)
from gunpla_fabrication_suite.shared_ui.toast import ToastOverlay
from gunpla_fabrication_suite.shell.command_palette import CommandPaletteDialog
from gunpla_fabrication_suite.shell.diagnostics_dialog import DiagnosticsDialog
from gunpla_fabrication_suite.shell.navigation import NavigationRail
from gunpla_fabrication_suite.shell.plugin_manager_page import PluginManagerPage
from gunpla_fabrication_suite.shell.widgets import AppStatusBar, InspectorPanel, WorkspaceStack

_CORE_PLUGIN_ID = "core"


class MainWindow(QMainWindow):
    """The application's top-level window."""

    def __init__(
        self,
        *,
        navigation: NavigationRegistry,
        dashboard_widgets: DashboardWidgetRegistry,
        commands: CommandRegistry,
        plugin_manager: PluginManager,
        database: DatabaseService,
        notifications: NotificationCenter,
        jobs: BackgroundJobManager,
        paths: ApplicationPaths,
        settings_service: SettingsService,
    ) -> None:
        super().__init__()
        self._navigation = navigation
        self._commands = commands
        self._plugin_manager = plugin_manager
        self._database = database
        self._notifications = notifications
        self._paths = paths
        self._settings_service = settings_service

        self.setWindowTitle("Gunpla Fabrication Suite")
        self.setMinimumSize(1024, 680)

        self._register_core_navigation(settings_service)
        self._register_core_commands()

        self._nav_rail = NavigationRail(navigation)
        self._workspace = WorkspaceStack()
        self._workspace.bind_registry(navigation)
        self._inspector = InspectorPanel()

        self._splitter = QSplitter()
        self._splitter.addWidget(self._nav_rail)
        self._splitter.addWidget(self._workspace)
        self._splitter.addWidget(self._inspector)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setObjectName("mainSplitter")
        self.setCentralWidget(self._splitter)

        self._nav_rail.page_selected.connect(self._workspace.show_page)
        first_page = next(iter(navigation.all_pages()), None)
        if first_page is not None:
            self._workspace.show_page(first_page.page_id)

        self._status_bar = AppStatusBar(
            jobs=jobs, notifications=notifications, plugin_manager=plugin_manager
        )
        self.setStatusBar(self._status_bar)

        self._toast_overlay = ToastOverlay(self._splitter)
        notifications.notification_posted.connect(self._toast_overlay.show_notification)

        self._build_menu_bar()
        self._restore_window_state()

    def _register_core_navigation(self, settings_service: SettingsService) -> None:
        self._navigation.register(
            _CORE_PLUGIN_ID,
            NavigationPageContribution(
                page_id="core.plugin_manager",
                title="Plugin Manager",
                factory=lambda: PluginManagerPage(self._plugin_manager, settings_service),
                section="secondary",
                order=900,
            ),
        )

    def _register_core_commands(self) -> None:
        self._commands.register(
            _CORE_PLUGIN_ID,
            CommandContribution(
                command_id="core.open_plugin_manager",
                title="Open Plugin Manager",
                callback=lambda: self._workspace.show_page("core.plugin_manager"),
            ),
        )
        self._commands.register(
            _CORE_PLUGIN_ID,
            CommandContribution(
                command_id="core.show_diagnostics",
                title="Show Diagnostics",
                callback=self._show_diagnostics,
            ),
        )
        self._commands.register(
            _CORE_PLUGIN_ID,
            CommandContribution(
                command_id="core.quit",
                title="Quit Gunpla Fabrication Suite",
                shortcut="Ctrl+Q",
                callback=self._quit,
            ),
        )

    def _build_menu_bar(self) -> None:
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")
        quit_action = QAction("&Quit", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        view_menu = menu_bar.addMenu("&View")
        palette_action = QAction("&Command Palette…", self)
        palette_action.setShortcut(QKeySequence("Ctrl+K"))
        palette_action.triggered.connect(self._open_command_palette)
        view_menu.addAction(palette_action)

        tools_menu = menu_bar.addMenu("&Tools")
        plugin_manager_action = QAction("&Plugin Manager", self)
        plugin_manager_action.triggered.connect(
            lambda: self._workspace.show_page("core.plugin_manager")
        )
        tools_menu.addAction(plugin_manager_action)

        help_menu = menu_bar.addMenu("&Help")
        diagnostics_action = QAction("&Diagnostics…", self)
        diagnostics_action.triggered.connect(self._show_diagnostics)
        help_menu.addAction(diagnostics_action)
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _quit(self) -> None:
        self.close()

    def _open_command_palette(self) -> None:
        dialog = CommandPaletteDialog(self._commands, self)
        dialog.move(
            self.geometry().center().x() - dialog.width() // 2,
            self.geometry().top() + 80,
        )
        dialog.show()

    def _show_diagnostics(self) -> None:
        dialog = DiagnosticsDialog(
            paths=self._paths,
            database=self._database,
            plugin_manager=self._plugin_manager,
            parent=self,
        )
        dialog.exec()

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About Gunpla Fabrication Suite",
            f"Gunpla Fabrication Suite {__version__}\n\n"
            "A premium, offline-first workshop management application for Gunpla builders.\n\n"
            "Adeptus Craftmatica",
        )

    def _qsettings(self) -> QSettings:
        return QSettings()

    def _restore_window_state(self) -> None:
        settings = self._qsettings()
        geometry = settings.value("window/geometry")
        if isinstance(geometry, QByteArray):
            self.restoreGeometry(geometry)
        else:
            self.resize(1280, 800)

        splitter_state = settings.value("window/splitter")
        if isinstance(splitter_state, QByteArray):
            self._splitter.restoreState(splitter_state)
        else:
            self._splitter.setSizes([200, 800, 280])

    def closeEvent(self, event: QCloseEvent) -> None:
        settings = self._qsettings()
        settings.setValue("window/geometry", self.saveGeometry())
        settings.setValue("window/splitter", self._splitter.saveState())
        self._plugin_manager.shutdown_all()
        super().closeEvent(event)


def configure_qsettings_identity() -> None:
    """Set the organization/application identity used by :class:`QSettings`.

    Must be called once, before any :class:`QSettings` instance is created.
    """
    QApplication.setOrganizationName("Adeptus Craftmatica")
    QApplication.setOrganizationDomain("adeptuscraftmatica.dev")
    QApplication.setApplicationName("Gunpla Fabrication Suite")
