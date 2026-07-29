"""Tests for plugin discovery, dependency ordering, and failure isolation."""

from __future__ import annotations

import shutil
from pathlib import Path

from gunpla_fabrication_suite.core.events import EventBus
from gunpla_fabrication_suite.core.notifications import NotificationCenter
from gunpla_fabrication_suite.core.persistence import DatabaseService
from gunpla_fabrication_suite.core.plugins import PluginManager, PluginStatus
from gunpla_fabrication_suite.core.services import ServiceContainer
from gunpla_fabrication_suite.plugin_sdk.registries import (
    CommandRegistry,
    DashboardWidgetRegistry,
    NavigationRegistry,
)

_FIXTURE_PLUGINS_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "plugins"


def _install_fixture_plugin(app_paths, name: str) -> None:
    shutil.copytree(_FIXTURE_PLUGINS_ROOT / name, app_paths.plugins_dir / name)


def _make_manager(app_paths, database: DatabaseService, qapp) -> PluginManager:
    return PluginManager(
        services=ServiceContainer(),
        events=EventBus(),
        database=database,
        notifications=NotificationCenter(),
        paths=app_paths,
        navigation=NavigationRegistry(),
        dashboard_widgets=DashboardWidgetRegistry(),
        commands=CommandRegistry(),
    )


def test_builtin_plugins_are_discovered_and_started(app_paths, database, qapp) -> None:
    manager = _make_manager(app_paths, database, qapp)

    manager.discover_and_load()

    ids = {record.manifest.id for record in manager.records}
    assert "com.adeptuscraftmatica.gfs.dashboard" in ids
    assert "com.adeptuscraftmatica.gfs.kit_library" in ids
    for record in manager.records:
        assert record.status == PluginStatus.STARTED
        assert record.health.value == "healthy"


def test_broken_plugin_is_isolated_without_affecting_others(app_paths, database, qapp) -> None:
    _install_fixture_plugin(app_paths, "broken_plugin")
    manager = _make_manager(app_paths, database, qapp)

    manager.discover_and_load()

    broken = manager.get("test.plugin.broken")
    assert broken is not None
    assert broken.status == PluginStatus.FAILED
    assert broken.health.value == "unhealthy"
    assert "intentionally broken" in (broken.error or "")

    dashboard = manager.get("com.adeptuscraftmatica.gfs.dashboard")
    assert dashboard is not None
    assert dashboard.status == PluginStatus.STARTED


def test_dependent_plugin_loads_after_its_dependency(app_paths, database, qapp) -> None:
    _install_fixture_plugin(app_paths, "plugin_a")
    _install_fixture_plugin(app_paths, "plugin_b")
    manager = _make_manager(app_paths, database, qapp)

    manager.discover_and_load()

    assert manager.get("test.plugin.a").status == PluginStatus.STARTED
    assert manager.get("test.plugin.b").status == PluginStatus.STARTED

    log_path = app_paths.root / "load_order.log"
    order = log_path.read_text(encoding="utf-8").splitlines()
    assert order.index("test.plugin.a") < order.index("test.plugin.b")


def test_disabled_plugin_is_not_started(app_paths, database, qapp) -> None:
    manager = PluginManager(
        services=ServiceContainer(),
        events=EventBus(),
        database=database,
        notifications=NotificationCenter(),
        paths=app_paths,
        navigation=NavigationRegistry(),
        dashboard_widgets=DashboardWidgetRegistry(),
        commands=CommandRegistry(),
        disabled_plugin_ids=frozenset({"com.adeptuscraftmatica.gfs.dashboard"}),
    )

    manager.discover_and_load()

    dashboard = manager.get("com.adeptuscraftmatica.gfs.dashboard")
    assert dashboard.status == PluginStatus.DISABLED
