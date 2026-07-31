"""Tests for the Supplies page: listing, filtering, archiving, and restoring."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QLabel

from gunpla_fabrication_suite.core.events import EventBus
from gunpla_fabrication_suite.core.notifications import NotificationCenter
from gunpla_fabrication_suite.core.persistence import DatabaseService
from gunpla_fabrication_suite.plugins.supplies.models.supply import SupplyCategory
from gunpla_fabrication_suite.plugins.supplies.repositories.supply_repository import (
    SupplyRepository,
)
from gunpla_fabrication_suite.plugins.supplies.schemas import SupplyCreate
from gunpla_fabrication_suite.plugins.supplies.services.supply_service import SupplyService
from gunpla_fabrication_suite.plugins.supplies.ui import supplies_page as supplies_page_module
from gunpla_fabrication_suite.plugins.supplies.ui.supplies_page import SuppliesPage


@pytest.fixture
def supply_service(database: DatabaseService, event_bus: EventBus) -> SupplyService:
    return SupplyService(SupplyRepository(database), event_bus)


@pytest.fixture
def page(qtbot, supply_service: SupplyService, inspector) -> SuppliesPage:
    widget = SuppliesPage(supply_service, NotificationCenter(), inspector)
    qtbot.addWidget(widget)
    return widget


def _payload(name: str, **overrides: object) -> SupplyCreate:
    defaults: dict[str, object] = {"brand": "Mr. Color", "name": name}
    defaults.update(overrides)
    return SupplyCreate(**defaults)  # type: ignore[arg-type]


def test_empty_supplies_shows_empty_state(page: SuppliesPage) -> None:
    assert page._stack.currentWidget() is page._empty_state


def test_created_supplies_appear_in_the_table(
    supply_service: SupplyService, page: SuppliesPage
) -> None:
    supply_service.create_supply(_payload("Gundam Gray"))
    supply_service.create_supply(_payload("Extra Thin Cement", category=SupplyCategory.CEMENT))

    page._reload()

    assert page._stack.currentWidget() is page._table
    assert page._table.rowCount() == 2


def test_search_filters_rows_by_name(supply_service: SupplyService, page: SuppliesPage) -> None:
    supply_service.create_supply(_payload("Gundam Gray"))
    supply_service.create_supply(_payload("Zaku Green"))
    page._reload()

    page._search_edit.setText("zaku")

    assert page._table.rowCount() == 1
    assert page._table.item(0, 0).text() == "Zaku Green"


def test_category_filter_narrows_rows(supply_service: SupplyService, page: SuppliesPage) -> None:
    supply_service.create_supply(_payload("Gundam Gray", category=SupplyCategory.PAINT))
    supply_service.create_supply(
        _payload("Extra Thin Cement", category=SupplyCategory.CEMENT)
    )
    page._reload()

    index = page._category_combo.findData(SupplyCategory.CEMENT)
    assert index >= 0
    page._category_combo.setCurrentIndex(index)

    assert page._table.rowCount() == 1
    assert page._table.item(0, 0).text() == "Extra Thin Cement"


def test_archive_hides_supply_and_restore_brings_it_back(
    monkeypatch, supply_service: SupplyService, page: SuppliesPage
) -> None:
    monkeypatch.setattr(
        supplies_page_module, "confirm_destructive_action", lambda *a, **k: True
    )
    supply_service.create_supply(_payload("Gundam Gray"))
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
    assert not supply_service.list_supplies()[0].is_deleted


def test_archive_declined_by_user_keeps_supply_active(
    monkeypatch, supply_service: SupplyService, page: SuppliesPage
) -> None:
    monkeypatch.setattr(
        supplies_page_module, "confirm_destructive_action", lambda *a, **k: False
    )
    supply_service.create_supply(_payload("Gundam Gray"))
    page._reload()
    page._table.selectRow(0)

    page._on_archive()

    assert page._table.rowCount() == 1


def test_selecting_a_row_pushes_details_into_the_inspector(
    supply_service: SupplyService, page: SuppliesPage, inspector
) -> None:
    supply_service.create_supply(_payload("Gundam Gray"))
    page._reload()

    page._table.selectRow(0)

    detail_widget = inspector._details_layout.itemAt(0).widget()
    name_label = detail_widget.layout().itemAt(0).widget()
    assert isinstance(name_label, QLabel)
    assert name_label.text() == "Gundam Gray"


def test_deselecting_clears_the_inspector(
    supply_service: SupplyService, page: SuppliesPage
) -> None:
    supply_service.create_supply(_payload("Gundam Gray"))
    page._reload()
    page._table.selectRow(0)

    page._table.clearSelection()
    page._update_action_buttons()

    placeholder = page._inspector._details_layout.itemAt(0).widget()
    assert isinstance(placeholder, QLabel)
    assert placeholder.text() == "Nothing selected."


def test_show_supply_selects_the_matching_row(
    supply_service: SupplyService, page: SuppliesPage
) -> None:
    supply_service.create_supply(_payload("Gundam Gray"))
    target = supply_service.create_supply(_payload("Panel Liner"))
    page._reload()

    page.show_supply(target.id)

    selected = page._selected_supply()
    assert selected is not None
    assert selected.id == target.id


def test_show_supply_reveals_an_archived_supply_by_checking_show_archived(
    supply_service: SupplyService, page: SuppliesPage
) -> None:
    target = supply_service.create_supply(_payload("Gundam Gray"))
    supply_service.archive_supply(target.id)
    page._reload()
    assert page._table.rowCount() == 0

    page.show_supply(target.id)

    assert page._show_archived_checkbox.isChecked() is True
    selected = page._selected_supply()
    assert selected is not None
    assert selected.id == target.id
