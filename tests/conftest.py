"""Shared pytest fixtures."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from gunpla_fabrication_suite.core.events import EventBus
from gunpla_fabrication_suite.core.jobs import BackgroundJobManager
from gunpla_fabrication_suite.core.layout import LayoutManager
from gunpla_fabrication_suite.core.navigation import Navigator
from gunpla_fabrication_suite.core.paths import ApplicationPaths
from gunpla_fabrication_suite.core.persistence import DatabaseService
from gunpla_fabrication_suite.core.settings import SettingsService
from gunpla_fabrication_suite.core.theming import ThemeManager
from gunpla_fabrication_suite.plugins.build_planner.repositories.build_repository import (
    BuildRepository,
)
from gunpla_fabrication_suite.plugins.build_planner.repositories.journal_repository import (
    JournalRepository,
)
from gunpla_fabrication_suite.plugins.build_planner.repositories.supply_usage_repository import (
    SupplyUsageRepository,
)
from gunpla_fabrication_suite.plugins.build_planner.repositories.work_session_repository import (
    WorkSessionRepository,
)
from gunpla_fabrication_suite.plugins.build_planner.services.build_service import BuildService
from gunpla_fabrication_suite.plugins.build_planner.services.journal_service import JournalService
from gunpla_fabrication_suite.plugins.build_planner.services.supply_usage_service import (
    SupplyUsageService,
)
from gunpla_fabrication_suite.plugins.build_planner.services.work_session_service import (
    WorkSessionService,
)
from gunpla_fabrication_suite.plugins.kit_library.repositories.kit_repository import KitRepository
from gunpla_fabrication_suite.plugins.kit_library.schemas import KitCreate
from gunpla_fabrication_suite.plugins.kit_library.services.kit_service import KitService
from gunpla_fabrication_suite.plugins.photography.repositories import PhotoRepository
from gunpla_fabrication_suite.plugins.photography.services import PhotoService
from gunpla_fabrication_suite.plugins.supplies.repositories.supply_repository import (
    SupplyRepository,
)
from gunpla_fabrication_suite.plugins.supplies.schemas import SupplyCreate
from gunpla_fabrication_suite.plugins.supplies.services.supply_service import SupplyService
from gunpla_fabrication_suite.shared_ui import InspectorPanel


@pytest.fixture
def app_paths(tmp_path):
    """A fully isolated set of application directories under pytest's tmp_path."""
    paths = ApplicationPaths(root=tmp_path)
    paths.ensure_exists()
    return paths


@pytest.fixture
def database(app_paths):
    """A migrated, isolated SQLite database for the duration of one test."""
    db = DatabaseService(app_paths.database_file)
    db.migrate()
    yield db
    db.dispose()


@pytest.fixture
def event_bus():
    """A fresh, empty event bus."""
    return EventBus()


@pytest.fixture
def kit_service(database, event_bus):
    """A Kit Library service backed by the isolated test database."""
    return KitService(KitRepository(database), event_bus)


@pytest.fixture
def existing_kit(kit_service):
    """A single kit already saved, for tests that need a build to point at."""
    return kit_service.create_kit(
        KitCreate(manufacturer="Bandai", name="RX-78-2 Gundam", grade="HG")
    )


@pytest.fixture
def build_service(database, kit_service, event_bus):
    """A Build Planner service backed by the isolated test database."""
    return BuildService(BuildRepository(database), kit_service, event_bus)


@pytest.fixture
def work_session_service(database, event_bus):
    """A work-session timer service backed by the isolated test database."""
    return WorkSessionService(WorkSessionRepository(database), event_bus)


@pytest.fixture
def journal_service(database):
    """A build journal service backed by the isolated test database."""
    return JournalService(JournalRepository(database))


@pytest.fixture
def photo_service(database, app_paths, event_bus):
    """A Photography service backed by the isolated test database and media directories."""
    return PhotoService(PhotoRepository(database), app_paths, event_bus)


@pytest.fixture
def supply_service(database, event_bus):
    """A Supplies service backed by the isolated test database."""
    return SupplyService(SupplyRepository(database), event_bus)


@pytest.fixture
def existing_supply(supply_service):
    """A single priced supply already saved, for tests that need one to log usage against."""
    return supply_service.create_supply(
        SupplyCreate(
            brand="Mr. Color", name="Gundam Gray", quantity_on_hand=10, purchase_price_cents=500
        )
    )


@pytest.fixture
def supply_usage_service(database, supply_service, event_bus):
    """A Build Planner supply-usage service backed by the isolated test database."""
    return SupplyUsageService(SupplyUsageRepository(database), supply_service, event_bus)


@pytest.fixture
def jobs():
    """A fresh background job manager."""
    manager = BackgroundJobManager()
    yield manager


@pytest.fixture
def navigator():
    """A fresh page-navigation broadcaster."""
    return Navigator()


@pytest.fixture
def settings_service(app_paths):
    """A settings service backed by the isolated test app_paths."""
    return SettingsService(app_paths.settings_file)


@pytest.fixture
def theme_manager(qapp, settings_service):
    """A theme manager applying to the real, shared pytest-qt QApplication."""
    return ThemeManager(qapp, settings_service)


@pytest.fixture
def layout_manager(settings_service):
    """A fresh layout manager backed by the isolated test settings."""
    return LayoutManager(settings_service)


@pytest.fixture
def inspector():
    """A fresh shared Inspector panel, as threaded through PluginContext."""
    return InspectorPanel()
