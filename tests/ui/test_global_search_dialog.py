"""Tests for the Global Search popup: filtering and result activation."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QWidget

from gunpla_fabrication_suite.plugin_sdk.contracts import NavigationPageContribution
from gunpla_fabrication_suite.plugin_sdk.registries import NavigationRegistry
from gunpla_fabrication_suite.plugins.kit_library.schemas import KitCreate
from gunpla_fabrication_suite.plugins.search.services.search_index_service import (
    SearchIndexService,
)
from gunpla_fabrication_suite.plugins.search.ui.global_search_dialog import GlobalSearchDialog


@pytest.fixture
def navigation():
    return NavigationRegistry()


@pytest.fixture
def index_service(kit_service, build_service, photo_service, supply_service):
    return SearchIndexService(kit_service, build_service, photo_service, supply_service)


def test_selecting_a_result_calls_focus_before_navigating(
    qtbot, kit_service, index_service, navigation, navigator, existing_kit
) -> None:
    calls: list[str] = []
    order: list[str] = []
    navigation.register(
        "kit_library",
        NavigationPageContribution(
            page_id="kit_library",
            title="Kit Library",
            factory=lambda: QWidget(),
            focus=lambda kit_id: (calls.append(kit_id), order.append("focus")),
        ),
    )
    navigator.navigate_requested.connect(lambda page_id: order.append(f"navigate:{page_id}"))

    dialog = GlobalSearchDialog(index_service, navigation, navigator)
    qtbot.addWidget(dialog)
    dialog._search_box.setText(existing_kit.name)

    dialog._activate(dialog._results.item(0))

    assert calls == [existing_kit.id]
    assert order == ["focus", "navigate:kit_library"]


def test_escape_closes_the_dialog(qtbot, index_service, navigation, navigator) -> None:
    dialog = GlobalSearchDialog(index_service, navigation, navigator)
    qtbot.addWidget(dialog)
    dialog.show()

    dialog.keyPressEvent(
        QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
    )

    assert dialog.isVisible() is False


def test_no_matching_query_leaves_the_list_empty(
    qtbot, index_service, navigation, navigator, existing_kit
) -> None:
    dialog = GlobalSearchDialog(index_service, navigation, navigator)
    qtbot.addWidget(dialog)

    dialog._search_box.setText("zzzzzznotarealmatchzzzzzz")

    assert dialog._results.count() == 0


def test_results_are_capped_at_thirty(
    qtbot, kit_service, index_service, navigation, navigator
) -> None:
    for i in range(40):
        kit_service.create_kit(KitCreate(manufacturer="Bandai", name=f"Kit {i}", grade="HG"))

    dialog = GlobalSearchDialog(index_service, navigation, navigator)
    qtbot.addWidget(dialog)

    assert dialog._results.count() == 30
