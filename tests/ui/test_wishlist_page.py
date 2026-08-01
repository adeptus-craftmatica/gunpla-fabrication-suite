"""Tests for the Wishlist page: listing, filtering, archiving, restoring, and purchasing."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QLabel, QMessageBox

from gunpla_fabrication_suite.core.events import EventBus
from gunpla_fabrication_suite.core.notifications import NotificationCenter
from gunpla_fabrication_suite.core.persistence import DatabaseService
from gunpla_fabrication_suite.plugins.kit_library.models.kit import CollectionStatus
from gunpla_fabrication_suite.plugins.kit_library.services.kit_service import KitService
from gunpla_fabrication_suite.plugins.wishlist.models.wishlist_item import WishlistItemType
from gunpla_fabrication_suite.plugins.wishlist.repositories.wishlist_repository import (
    WishlistRepository,
)
from gunpla_fabrication_suite.plugins.wishlist.schemas import WishlistItemCreate
from gunpla_fabrication_suite.plugins.wishlist.services.wishlist_service import WishlistService
from gunpla_fabrication_suite.plugins.wishlist.ui import wishlist_page as wishlist_page_module
from gunpla_fabrication_suite.plugins.wishlist.ui.wishlist_page import WishlistPage


@pytest.fixture
def wishlist_service(database: DatabaseService, event_bus: EventBus) -> WishlistService:
    return WishlistService(WishlistRepository(database), event_bus)


@pytest.fixture
def page(
    qtbot, wishlist_service: WishlistService, kit_service: KitService, inspector
) -> WishlistPage:
    widget = WishlistPage(wishlist_service, kit_service, NotificationCenter(), inspector)
    qtbot.addWidget(widget)
    return widget


def _payload(name: str, **overrides: object) -> WishlistItemCreate:
    defaults: dict[str, object] = {"name": name}
    defaults.update(overrides)
    return WishlistItemCreate(**defaults)  # type: ignore[arg-type]


def test_empty_wishlist_shows_empty_state(page: WishlistPage) -> None:
    assert page._stack.currentWidget() is page._empty_state


def test_created_items_appear_in_the_table(
    wishlist_service: WishlistService, page: WishlistPage
) -> None:
    wishlist_service.create_item(_payload("RX-78-2 Gundam"))
    wishlist_service.create_item(_payload("Panel Liner", item_type=WishlistItemType.TOOL))

    page._reload()

    assert page._stack.currentWidget() is page._table
    assert page._table.rowCount() == 2


def test_search_filters_rows_by_name(
    wishlist_service: WishlistService, page: WishlistPage
) -> None:
    wishlist_service.create_item(_payload("RX-78-2 Gundam"))
    wishlist_service.create_item(_payload("Zaku II"))
    page._reload()

    page._search_edit.setText("zaku")

    assert page._table.rowCount() == 1
    assert page._table.item(0, 0).text() == "Zaku II"


def test_type_filter_narrows_rows(wishlist_service: WishlistService, page: WishlistPage) -> None:
    wishlist_service.create_item(_payload("RX-78-2 Gundam", item_type=WishlistItemType.KIT))
    wishlist_service.create_item(_payload("Panel Liner", item_type=WishlistItemType.TOOL))
    page._reload()

    index = page._type_combo.findData(WishlistItemType.TOOL)
    assert index >= 0
    page._type_combo.setCurrentIndex(index)

    assert page._table.rowCount() == 1
    assert page._table.item(0, 0).text() == "Panel Liner"


def test_archive_hides_item_and_restore_brings_it_back(
    monkeypatch, wishlist_service: WishlistService, page: WishlistPage
) -> None:
    monkeypatch.setattr(wishlist_page_module, "confirm_destructive_action", lambda *a, **k: True)
    wishlist_service.create_item(_payload("RX-78-2 Gundam"))
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
    assert not wishlist_service.list_items()[0].is_deleted


def test_archive_declined_by_user_keeps_item_active(
    monkeypatch, wishlist_service: WishlistService, page: WishlistPage
) -> None:
    monkeypatch.setattr(wishlist_page_module, "confirm_destructive_action", lambda *a, **k: False)
    wishlist_service.create_item(_payload("RX-78-2 Gundam"))
    page._reload()
    page._table.selectRow(0)

    page._on_archive()

    assert page._table.rowCount() == 1


def test_selecting_a_row_pushes_details_into_the_inspector(
    wishlist_service: WishlistService, page: WishlistPage, inspector
) -> None:
    wishlist_service.create_item(_payload("RX-78-2 Gundam"))
    page._reload()

    page._table.selectRow(0)

    detail_widget = inspector._details_layout.itemAt(0).widget()
    name_label = detail_widget.layout().itemAt(0).widget()
    assert isinstance(name_label, QLabel)
    assert name_label.text() == "RX-78-2 Gundam"


def test_show_item_selects_the_matching_row(
    wishlist_service: WishlistService, page: WishlistPage
) -> None:
    wishlist_service.create_item(_payload("RX-78-2 Gundam"))
    target = wishlist_service.create_item(_payload("Panel Liner"))
    page._reload()

    page.show_item(target.id)

    selected = page._selected_item()
    assert selected is not None
    assert selected.id == target.id


def test_marking_a_non_kit_item_purchased_needs_no_confirmation(
    wishlist_service: WishlistService, page: WishlistPage
) -> None:
    wishlist_service.create_item(_payload("Panel Liner", item_type=WishlistItemType.TOOL))
    page._reload()
    page._table.selectRow(0)

    page._on_mark_purchased()

    assert wishlist_service.list_items(include_purchased=True)[0].is_purchased is True
    # The default (unpurchased) view no longer shows it.
    assert page._table.rowCount() == 0


def test_marking_a_kit_item_purchased_creates_a_kit_library_entry(
    monkeypatch,
    wishlist_service: WishlistService,
    kit_service: KitService,
    page: WishlistPage,
) -> None:
    monkeypatch.setattr(
        wishlist_page_module.QMessageBox,
        "question",
        lambda *a, **k: QMessageBox.StandardButton.Yes,
    )
    monkeypatch.setattr(
        wishlist_page_module.KitFormDialog,
        "exec",
        lambda self: wishlist_page_module.KitFormDialog.DialogCode.Rejected,
    )

    wishlist_service.create_item(
        _payload("RX-78-2 Gundam", item_type=WishlistItemType.KIT, manufacturer="Bandai")
    )
    page._reload()
    page._table.selectRow(0)

    page._on_mark_purchased()

    assert wishlist_service.list_items(include_purchased=True)[0].is_purchased is True
    kits = kit_service.list_kits()
    assert len(kits) == 1
    assert kits[0].name == "RX-78-2 Gundam"
    assert kits[0].manufacturer == "Bandai"
    assert kits[0].status == CollectionStatus.OWNED_SEALED.value


def test_declining_the_kit_confirmation_does_not_mark_purchased_or_create_a_kit(
    monkeypatch,
    wishlist_service: WishlistService,
    kit_service: KitService,
    page: WishlistPage,
) -> None:
    monkeypatch.setattr(
        wishlist_page_module.QMessageBox,
        "question",
        lambda *a, **k: QMessageBox.StandardButton.No,
    )

    wishlist_service.create_item(_payload("RX-78-2 Gundam", item_type=WishlistItemType.KIT))
    page._reload()
    page._table.selectRow(0)

    page._on_mark_purchased()

    assert wishlist_service.list_items()[0].is_purchased is False
    assert kit_service.list_kits() == []
