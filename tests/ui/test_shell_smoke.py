"""End-to-end smoke tests for the application shell against a real, isolated stack."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QSettings

from gunpla_fabrication_suite.core.events import EventBus
from gunpla_fabrication_suite.core.jobs import BackgroundJobManager
from gunpla_fabrication_suite.core.navigation import Navigator
from gunpla_fabrication_suite.core.notifications import NotificationCenter
from gunpla_fabrication_suite.core.persistence import DatabaseService
from gunpla_fabrication_suite.core.plugins import PluginManager
from gunpla_fabrication_suite.core.services import ServiceContainer
from gunpla_fabrication_suite.plugin_sdk.registries import (
    CommandRegistry,
    DashboardWidgetRegistry,
    NavigationRegistry,
)
from gunpla_fabrication_suite.shell.command_palette import CommandPaletteDialog
from gunpla_fabrication_suite.shell.main_window import MainWindow


@pytest.fixture
def isolated_qsettings(tmp_path, monkeypatch):
    """Redirect QSettings to a temp .ini file so tests never touch real user prefs."""
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "qsettings")
    )
    monkeypatch.setattr("PySide6.QtWidgets.QApplication.organizationName", lambda: "GFS Tests")
    yield


@pytest.fixture
def shell(
    qtbot,
    app_paths,
    database: DatabaseService,
    isolated_qsettings,
    settings_service,
    theme_manager,
    layout_manager,
    inspector,
):
    navigation = NavigationRegistry()
    dashboard_widgets = DashboardWidgetRegistry()
    commands = CommandRegistry()
    notifications = NotificationCenter()
    jobs = BackgroundJobManager()
    navigator = Navigator()

    plugin_manager = PluginManager(
        services=ServiceContainer(),
        events=EventBus(),
        database=database,
        notifications=notifications,
        jobs=jobs,
        navigator=navigator,
        theme_manager=theme_manager,
        layout_manager=layout_manager,
        inspector=inspector,
        paths=app_paths,
        navigation=navigation,
        dashboard_widgets=dashboard_widgets,
        commands=commands,
    )
    plugin_manager.discover_and_load()

    window = MainWindow(
        navigation=navigation,
        dashboard_widgets=dashboard_widgets,
        commands=commands,
        plugin_manager=plugin_manager,
        database=database,
        notifications=notifications,
        jobs=jobs,
        navigator=navigator,
        theme_manager=theme_manager,
        layout_manager=layout_manager,
        inspector=inspector,
        paths=app_paths,
        settings_service=settings_service,
    )
    qtbot.addWidget(window)
    return window


def test_main_window_registers_core_and_plugin_navigation(shell: MainWindow) -> None:
    page_ids = {page.page_id for page in shell._navigation.all_pages()}

    assert "dashboard" in page_ids
    assert "kit_library" in page_ids
    assert "core.plugin_manager" in page_ids


def test_selecting_a_nav_page_shows_it_in_the_workspace(shell: MainWindow) -> None:
    shell._workspace.show_page("kit_library")

    from gunpla_fabrication_suite.plugins.kit_library.ui.kit_library_page import KitLibraryPage

    assert isinstance(shell._workspace.currentWidget(), KitLibraryPage)


def test_command_palette_lists_core_commands(shell: MainWindow, qtbot) -> None:
    dialog = CommandPaletteDialog(shell._commands)
    qtbot.addWidget(dialog)

    titles = [dialog._results.item(i).text() for i in range(dialog._results.count())]

    assert any("Plugin Manager" in title for title in titles)
    assert any("Diagnostics" in title for title in titles)


def test_command_palette_filters_by_query(shell: MainWindow, qtbot) -> None:
    dialog = CommandPaletteDialog(shell._commands)
    qtbot.addWidget(dialog)

    dialog._search_box.setText("diagnostics")

    titles = [dialog._results.item(i).text() for i in range(dialog._results.count())]
    assert all("Diagnostics" in title for title in titles)
    assert len(titles) >= 1


def test_plugin_manager_page_lists_started_plugins(shell: MainWindow) -> None:
    shell._workspace.show_page("core.plugin_manager")

    from gunpla_fabrication_suite.shell.plugin_manager_page import PluginManagerPage

    page = shell._workspace.currentWidget()
    assert isinstance(page, PluginManagerPage)
    assert page._table.rowCount() >= 2


def test_window_opens_maximized_on_first_launch(shell: MainWindow) -> None:
    assert shell.isMaximized() is True


def test_layout_can_be_switched_back_and_forth_repeatedly(shell: MainWindow, qtbot) -> None:
    """Regression: switching layouts left whichever nav widget (_nav_rail /
    _top_nav_bar / _compact_rail / _diorama_overlay) the new layout doesn't
    use still parented to the outgoing central widget, so its deleteLater()
    destroyed that nav widget too — breaking the very next switch back to a
    layout that needed it."""
    from gunpla_fabrication_suite.core.layout import COMMAND_DECK, DIORAMA, RAIL, WORKBENCH

    layout_manager = shell._layout_manager
    for layout_id in (
        COMMAND_DECK,
        RAIL,
        WORKBENCH,
        DIORAMA,
        RAIL,
        DIORAMA,
        WORKBENCH,
        COMMAND_DECK,
        RAIL,
    ):
        layout_manager.set_layout(layout_id)
        qtbot.wait(10)  # let any deleteLater() from the switch actually run
        shell.navigate_to("dashboard")
