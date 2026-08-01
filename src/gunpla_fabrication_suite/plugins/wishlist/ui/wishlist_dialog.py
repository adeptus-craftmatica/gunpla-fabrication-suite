"""The add/edit wishlist item dialog."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from gunpla_fabrication_suite.plugins.wishlist.models.wishlist_item import WishlistItemType
from gunpla_fabrication_suite.plugins.wishlist.schemas import WishlistItemCreate, WishlistItemRead
from gunpla_fabrication_suite.themes import PALETTE

_TYPE_LABELS = {item_type: item_type.value.title() for item_type in WishlistItemType}


class WishlistItemFormDialog(QDialog):
    """A modal form for creating or editing a single wishlist item."""

    def __init__(
        self, *, existing: WishlistItemRead | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._existing = existing
        self.setWindowTitle("Edit Wishlist Item" if existing else "Add Wishlist Item")
        self.setMinimumWidth(440)

        outer = QVBoxLayout(self)

        self._error_label = QLabel()
        self._error_label.setStyleSheet(f"color: {PALETTE.danger};")
        self._error_label.hide()
        outer.addWidget(self._error_label)

        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
        outer.addLayout(form)

        self._type_combo = QComboBox()
        for item_type, label in _TYPE_LABELS.items():
            self._type_combo.addItem(label, item_type)
        form.addRow("Type", self._type_combo)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. RX-78-2 Gundam")
        form.addRow("Name*", self._name_edit)

        self._manufacturer_edit = QLineEdit()
        self._manufacturer_edit.setPlaceholderText("e.g. Bandai")
        form.addRow("Manufacturer", self._manufacturer_edit)

        self._priority_spin = QSpinBox()
        self._priority_spin.setRange(0, 5)
        form.addRow("Priority (0-5)", self._priority_spin)

        self._estimated_price_spin = QDoubleSpinBox()
        self._estimated_price_spin.setRange(0, 100_000)
        self._estimated_price_spin.setDecimals(2)
        self._estimated_price_spin.setPrefix("$")
        form.addRow("Estimated price", self._estimated_price_spin)

        self._tags_edit = QLineEdit()
        self._tags_edit.setPlaceholderText("comma, separated, tags")
        form.addRow("Tags", self._tags_edit)

        self._notes_edit = QPlainTextEdit()
        self._notes_edit.setFixedHeight(80)
        form.addRow("Notes", self._notes_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

        self._result_data: WishlistItemCreate | None = None
        if existing is not None:
            self._populate_from(existing)

    def _populate_from(self, item: WishlistItemRead) -> None:
        index = self._type_combo.findData(WishlistItemType(item.item_type))
        if index >= 0:
            self._type_combo.setCurrentIndex(index)
        self._name_edit.setText(item.name)
        self._manufacturer_edit.setText(item.manufacturer or "")
        self._priority_spin.setValue(item.priority)
        self._estimated_price_spin.setValue((item.estimated_price_cents or 0) / 100)
        self._tags_edit.setText(", ".join(item.tags))
        self._notes_edit.setPlainText(item.notes or "")

    def _on_accept(self) -> None:
        name = self._name_edit.text().strip()

        if not name:
            self._error_label.setText("Name is required.")
            self._error_label.show()
            return

        self._result_data = WishlistItemCreate(
            item_type=self._type_combo.currentData(),
            name=name,
            manufacturer=self._manufacturer_edit.text().strip() or None,
            priority=self._priority_spin.value(),
            estimated_price_cents=round(self._estimated_price_spin.value() * 100) or None,
            tags=[tag.strip() for tag in self._tags_edit.text().split(",") if tag.strip()],
            notes=self._notes_edit.toPlainText().strip() or None,
        )
        self.accept()

    def result_data(self) -> WishlistItemCreate | None:
        """The validated form data, populated only after a successful accept."""
        return self._result_data
