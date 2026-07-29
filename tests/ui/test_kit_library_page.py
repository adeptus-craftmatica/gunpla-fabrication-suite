"""Tests for the Kit Library page: listing, filtering, archiving, and restoring."""

from __future__ import annotations

import pytest

from gunpla_fabrication_suite.core.events import EventBus
from gunpla_fabrication_suite.core.notifications import NotificationCenter
from gunpla_fabrication_suite.core.persistence import DatabaseService
from gunpla_fabrication_suite.plugins.kit_library.repositories.kit_repository import KitRepository
from gunpla_fabrication_suite.plugins.kit_library.schemas import KitCreate
from gunpla_fabrication_suite.plugins.kit_library.services.kit_service import KitService
from gunpla_fabrication_suite.plugins.kit_library.ui import (
    kit_library_page as kit_library_page_module,
)
from gunpla_fabrication_suite.plugins.kit_library.ui.kit_library_page import KitLibraryPage


@pytest.fixture
def kit_service(database: DatabaseService, event_bus: EventBus) -> KitService:
    return KitService(KitRepository(database), event_bus)


@pytest.fixture
def page(qtbot, kit_service: KitService) -> KitLibraryPage:
    widget = KitLibraryPage(kit_service, NotificationCenter())
    qtbot.addWidget(widget)
    return widget


def _payload(name: str) -> KitCreate:
    return KitCreate(manufacturer="Bandai", name=name, grade="HG")


def test_empty_library_shows_empty_state(page: KitLibraryPage) -> None:
    assert page._stack.currentWidget() is page._empty_state


def test_created_kits_appear_in_the_table(kit_service: KitService, page: KitLibraryPage) -> None:
    kit_service.create_kit(_payload("RX-78-2 Gundam"))
    kit_service.create_kit(_payload("Zaku II"))

    page._reload()

    assert page._stack.currentWidget() is page._table
    assert page._table.rowCount() == 2


def test_search_filters_rows_by_name(kit_service: KitService, page: KitLibraryPage) -> None:
    kit_service.create_kit(_payload("RX-78-2 Gundam"))
    kit_service.create_kit(_payload("Zaku II"))
    page._reload()

    page._search_edit.setText("zaku")

    assert page._table.rowCount() == 1
    assert page._table.item(0, 0).text() == "Zaku II"


def test_archive_hides_kit_and_restore_brings_it_back(
    monkeypatch, kit_service: KitService, page: KitLibraryPage
) -> None:
    monkeypatch.setattr(kit_library_page_module, "confirm_destructive_action", lambda *a, **k: True)
    kit_service.create_kit(_payload("RX-78-2 Gundam"))
    page._reload()
    page._table.selectRow(0)

    page._on_archive()

    assert page._table.rowCount() == 0

    page._show_archived_checkbox.setChecked(True)
    assert page._table.rowCount() == 1
    page._table.selectRow(0)
    page._update_action_buttons()
    assert page._restore_button.isEnabled()

    page._on_restore()

    assert page._table.rowCount() == 1
    assert not kit_service.list_kits()[0].is_deleted


def test_archive_declined_by_user_keeps_kit_active(
    monkeypatch, kit_service: KitService, page: KitLibraryPage
) -> None:
    monkeypatch.setattr(
        kit_library_page_module, "confirm_destructive_action", lambda *a, **k: False
    )
    kit_service.create_kit(_payload("RX-78-2 Gundam"))
    page._reload()
    page._table.selectRow(0)

    page._on_archive()

    assert page._table.rowCount() == 1
