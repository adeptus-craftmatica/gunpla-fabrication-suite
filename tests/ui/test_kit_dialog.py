"""Tests for the add/edit kit form dialog's validation and data extraction."""

from __future__ import annotations

from gunpla_fabrication_suite.plugins.kit_library.models.kit import CollectionStatus
from gunpla_fabrication_suite.plugins.kit_library.ui.kit_dialog import KitFormDialog


def test_accept_with_required_fields_populates_result_data(qtbot) -> None:
    dialog = KitFormDialog()
    qtbot.addWidget(dialog)

    dialog._name_edit.setText("RX-78-2 Gundam")
    dialog._manufacturer_edit.setText("Bandai")
    dialog._grade_combo.setCurrentText("HG")
    dialog._priority_spin.setValue(2)
    dialog._tags_edit.setText("gundam, hg, priority")

    dialog._on_accept()

    result = dialog.result_data()
    assert result is not None
    assert result.name == "RX-78-2 Gundam"
    assert result.manufacturer == "Bandai"
    assert result.grade == "HG"
    assert result.priority == 2
    assert result.tags == ["gundam", "hg", "priority"]
    assert result.status == CollectionStatus.WISHLIST


def test_accept_without_required_fields_shows_error_and_keeps_result_none(qtbot) -> None:
    dialog = KitFormDialog()
    qtbot.addWidget(dialog)
    dialog.show()

    dialog._on_accept()

    assert dialog.result_data() is None
    assert dialog._error_label.isVisible()


def test_purchase_price_is_converted_to_cents(qtbot) -> None:
    dialog = KitFormDialog()
    qtbot.addWidget(dialog)

    dialog._name_edit.setText("Zaku II")
    dialog._manufacturer_edit.setText("Bandai")
    dialog._grade_combo.setCurrentText("MG")
    dialog._purchase_price_spin.setValue(24.99)

    dialog._on_accept()

    assert dialog.result_data().purchase_price_cents == 2499
