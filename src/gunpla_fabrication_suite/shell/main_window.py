"""The main window: composes navigation, workspace, inspector, and status bar.

This module only wires widgets together; it must not contain business logic.
Each piece it composes (navigation rail, workspace stack, inspector,
status bar, plugin manager page, diagnostics dialog) lives in its own module.
"""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QSettings
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from gunpla_fabrication_suite import __version__
from gunpla_fabrication_suite.core.jobs import BackgroundJobManager
from gunpla_fabrication_suite.core.layout import COMMAND_DECK, DIORAMA, WORKBENCH, LayoutManager
from gunpla_fabrication_suite.core.navigation import Navigator
from gunpla_fabrication_suite.core.notifications import NotificationCenter
from gunpla_fabrication_suite.core.paths import ApplicationPaths
from gunpla_fabrication_suite.core.persistence import DatabaseService
from gunpla_fabrication_suite.core.plugins import PluginManager
from gunpla_fabrication_suite.core.settings import SettingsService
from gunpla_fabrication_suite.core.theming import ThemeManager
from gunpla_fabrication_suite.plugin_sdk.contracts import (
    CommandContribution,
    NavigationPageContribution,
)
from gunpla_fabrication_suite.plugin_sdk.registries import (
    CommandRegistry,
    DashboardWidgetRegistry,
    NavigationRegistry,
)
from gunpla_fabrication_suite.shared_ui import InspectorPanel
from gunpla_fabrication_suite.shared_ui.toast import ToastOverlay
from gunpla_fabrication_suite.shell.appearance_page import AppearancePage
from gunpla_fabrication_suite.shell.backup_restore_page import BackupRestorePage
from gunpla_fabrication_suite.shell.command_palette import CommandPaletteDialog
from gunpla_fabrication_suite.shell.diagnostics_dialog import DiagnosticsDialog
from gunpla_fabrication_suite.shell.navigation import (
    CompactRail,
    DioramaNavOverlay,
    NavigationRail,
    TopNavBar,
)
from gunpla_fabrication_suite.shell.plugin_manager_page import PluginManagerPage
from gunpla_fabrication_suite.shell.widgets import AppStatusBar, WorkspaceStack

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
        navigator: Navigator,
        theme_manager: ThemeManager,
        layout_manager: LayoutManager,
        inspector: InspectorPanel,
        paths: ApplicationPaths,
        settings_service: SettingsService,
    ) -> None:
        super().__init__()
        self._navigation = navigation
        self._commands = commands
        self._plugin_manager = plugin_manager
        self._database = database
        self._notifications = notifications
        self._theme_manager = theme_manager
        self._layout_manager = layout_manager
        self._paths = paths
        self._settings_service = settings_service

        self.setWindowTitle("Gunpla Fabrication Suite")
        self.setMinimumSize(1024, 680)

        self._register_core_navigation(settings_service)
        self._register_core_commands()

        # All three nav widgets are built once and kept alive for the
        # window's whole lifetime, even while only one is actually on
        # screen — that way switching layouts never has to reconstruct or
        # re-wire any of them, and navigate_to() below can keep all three
        # permanently in sync.
        self._nav_rail = NavigationRail(navigation)
        self._top_nav_bar = TopNavBar(navigation)
        self._compact_rail = CompactRail(navigation)
        self._nav_rail.page_selected.connect(self.navigate_to)
        self._top_nav_bar.page_selected.connect(self.navigate_to)
        self._compact_rail.page_selected.connect(self.navigate_to)

        self._workspace = WorkspaceStack()
        self._workspace.bind_registry(navigation)
        # Constructed in bootstrap.py, not here — a page needs a live
        # reference to it (via PluginContext) to push contextual details,
        # and that reference must exist before plugin discovery runs, which
        # happens before MainWindow does.
        self._inspector = inspector

        self._splitter: QSplitter
        self._toast_overlay: ToastOverlay | None = None
        self._diorama_overlay: DioramaNavOverlay | None = None
        self._apply_shell_layout(layout_manager.current)
        assert self._toast_overlay is not None
        notifications.notification_posted.connect(self._toast_overlay.show_notification)
        layout_manager.layout_changed.connect(self._apply_shell_layout)

        navigator.navigate_requested.connect(self.navigate_to)
        first_page = next(iter(navigation.all_pages()), None)
        if first_page is not None:
            self.navigate_to(first_page.page_id)

        self._status_bar = AppStatusBar(
            jobs=jobs, notifications=notifications, plugin_manager=plugin_manager
        )
        self.setStatusBar(self._status_bar)

        self._build_menu_bar()
        self._restore_window_geometry()

    def _register_core_navigation(self, settings_service: SettingsService) -> None:
        self._navigation.register(
            _CORE_PLUGIN_ID,
            NavigationPageContribution(
                page_id="core.appearance",
                title="Appearance",
                factory=lambda: AppearancePage(self._theme_manager, self._layout_manager),
                section="secondary",
                order=800,
            ),
        )
        self._navigation.register(
            _CORE_PLUGIN_ID,
            NavigationPageContribution(
                page_id="core.backup_restore",
                title="Backup & Restore",
                factory=lambda: BackupRestorePage(
                    self._paths, self._database, self._notifications
                ),
                section="secondary",
                order=850,
            ),
        )
        self._navigation.register(
            _CORE_PLUGIN_ID,
            NavigationPageContribution(
                page_id="core.plugin_manager",
                title="Plugin Manager",
                factory=lambda: PluginManagerPage(
                    self._plugin_manager, settings_service, self._layout_manager, self._inspector
                ),
                section="secondary",
                order=900,
            ),
        )

    def _register_core_commands(self) -> None:
        self._commands.register(
            _CORE_PLUGIN_ID,
            CommandContribution(
                command_id="core.open_appearance",
                title="Open Appearance Settings",
                callback=lambda: self.navigate_to("core.appearance"),
            ),
        )
        self._commands.register(
            _CORE_PLUGIN_ID,
            CommandContribution(
                command_id="core.open_backup_restore",
                title="Open Backup & Restore",
                callback=lambda: self.navigate_to("core.backup_restore"),
            ),
        )
        self._commands.register(
            _CORE_PLUGIN_ID,
            CommandContribution(
                command_id="core.open_plugin_manager",
                title="Open Plugin Manager",
                callback=lambda: self.navigate_to("core.plugin_manager"),
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
        appearance_action = QAction("&Appearance…", self)
        appearance_action.triggered.connect(lambda: self.navigate_to("core.appearance"))
        view_menu.addAction(appearance_action)

        tools_menu = menu_bar.addMenu("&Tools")
        plugin_manager_action = QAction("&Plugin Manager", self)
        plugin_manager_action.triggered.connect(lambda: self.navigate_to("core.plugin_manager"))
        tools_menu.addAction(plugin_manager_action)

        help_menu = menu_bar.addMenu("&Help")
        diagnostics_action = QAction("&Diagnostics…", self)
        diagnostics_action.triggered.connect(self._show_diagnostics)
        help_menu.addAction(diagnostics_action)
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def navigate_to(self, page_id: str) -> None:
        """Switch the visible workspace page and keep every nav widget's selection in sync."""
        self._workspace.show_page(page_id)
        self._nav_rail.select(page_id)
        self._top_nav_bar.select(page_id)
        self._compact_rail.select(page_id)

    def _apply_shell_layout(self, layout_id: str) -> None:
        """Rebuild the shell's container arrangement for ``layout_id``, live.

        Reuses the already-live ``_workspace``/``_inspector``/``_nav_rail``/
        ``_top_nav_bar``/``_compact_rail`` instances by reparenting them —
        never reconstructs them, since ``WorkspaceStack`` caches every page
        it has ever built for the app's whole lifetime and losing that
        would drop live page state (open builds, in-progress timers, ...).
        """
        old_container = self.centralWidget()

        # Only some of these end up in the new arrangement below —
        # whichever ones don't must still be detached from the outgoing
        # container before it's deleted, or they get destroyed right along
        # with it (deleteLater() takes its whole child tree with it),
        # taking out the *next* switch back to a layout that needed them
        # with a dead widget. Diorama is the one layout that uses neither
        # the inspector nor any of the three "wide" nav widgets, which is
        # exactly why this must be unconditional, not layout-specific.
        self._nav_rail.setParent(None)
        self._top_nav_bar.setParent(None)
        self._compact_rail.setParent(None)
        self._inspector.setParent(None)
        if self._diorama_overlay is not None:
            self._diorama_overlay.setParent(None)

        if layout_id == COMMAND_DECK:
            container: QWidget = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(0)
            container_layout.addWidget(self._top_nav_bar)

            splitter = QSplitter()
            splitter.setObjectName("mainSplitter")
            splitter.addWidget(self._workspace)
            splitter.addWidget(self._inspector)
            splitter.setStretchFactor(0, 1)
            container_layout.addWidget(splitter, 1)
        elif layout_id == DIORAMA:
            # No nav pane and no inspector pane at all — content runs
            # full-bleed. The nav rail floats on top instead (see below),
            # collapsed to a thin edge strip until hovered.
            splitter = QSplitter()
            splitter.setObjectName("mainSplitter")
            splitter.addWidget(self._workspace)

            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.addWidget(splitter)
        else:
            nav_widget = self._compact_rail if layout_id == WORKBENCH else self._nav_rail
            splitter = QSplitter()
            splitter.setObjectName("mainSplitter")
            splitter.addWidget(nav_widget)
            splitter.addWidget(self._workspace)
            splitter.addWidget(self._inspector)
            splitter.setStretchFactor(1, 1)

            # Wrapped in a plain QWidget rather than using the splitter
            # itself as the container: ToastOverlay below gets parented to
            # whatever this container is, and a QSplitter treats *any*
            # child widget as a managed pane — even one never added via
            # addWidget() — which silently corrupts the size distribution
            # among the real panes once the overlay starts claiming space.
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.addWidget(splitter)

        self._splitter = splitter
        self._apply_default_splitter_sizes(layout_id)

        if self._toast_overlay is None:
            self._toast_overlay = ToastOverlay(container)
        else:
            self._toast_overlay.reparent_to(container)

        if layout_id == DIORAMA:
            if self._diorama_overlay is None:
                self._diorama_overlay = DioramaNavOverlay(self._nav_rail, container)
            else:
                self._diorama_overlay.reparent_to(container)
                # The unconditional self._nav_rail.setParent(None) detach
                # above strips nav_rail out of the overlay too, even when
                # re-entering Diorama with an already-existing overlay —
                # without this, the expanded overlay renders empty.
                self._diorama_overlay.attach_nav_rail()

        self.setCentralWidget(container)
        if old_container is not None:
            old_container.deleteLater()

    def _apply_default_splitter_sizes(self, layout_id: str) -> None:
        saved = self._qsettings().value(f"window/splitter/{layout_id}")
        if isinstance(saved, QByteArray):
            self._splitter.restoreState(saved)
            return
        if layout_id == COMMAND_DECK:
            # workspace | inspector (inspector collapsed by default — most
            # pages don't push anything into it yet).
            self._splitter.setSizes([1000, 0])
        elif layout_id == WORKBENCH:
            # compact rail | workspace | inspector — open wide by default,
            # since a populated Inspector is Workbench's whole point.
            self._splitter.setSizes([56, 664, 300])
        elif layout_id == DIORAMA:
            # workspace alone — the nav rail floats on top instead of
            # occupying a splitter pane (see _apply_shell_layout).
            self._splitter.setSizes([1000])
        else:
            # rail | workspace | inspector
            self._splitter.setSizes([220, 1000, 0])

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

    def _restore_window_geometry(self) -> None:
        settings = self._qsettings()
        geometry = settings.value("window/geometry")
        has_saved_geometry = isinstance(geometry, QByteArray)
        if has_saved_geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(1280, 800)

        # Default to maximized on first launch; afterwards, honor whatever
        # maximized/restored state the user last left the window in.
        was_maximized = settings.value("window/is_maximized", not has_saved_geometry, type=bool)
        if was_maximized:
            self.showMaximized()

    def closeEvent(self, event: QCloseEvent) -> None:
        settings = self._qsettings()
        settings.setValue("window/is_maximized", self.isMaximized())
        settings.setValue("window/geometry", self.saveGeometry())
        settings.setValue(
            f"window/splitter/{self._layout_manager.current}", self._splitter.saveState()
        )
        self._plugin_manager.shutdown_all()
        super().closeEvent(event)


def configure_qsettings_identity() -> None:
    """Set the organization/application identity used by :class:`QSettings`.

    Must be called once, before any :class:`QSettings` instance is created.
    """
    QApplication.setOrganizationName("Adeptus Craftmatica")
    QApplication.setOrganizationDomain("adeptuscraftmatica.dev")
    QApplication.setApplicationName("Gunpla Fabrication Suite")
