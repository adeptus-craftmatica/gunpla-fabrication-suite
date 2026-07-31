"""The add/edit supply dialog."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gunpla_fabrication_suite.plugins.supplies.models.supply import SupplyCategory
from gunpla_fabrication_suite.plugins.supplies.schemas import SupplyCreate, SupplyRead
from gunpla_fabrication_suite.themes import PALETTE

_UNITS = ("bottle", "ml", "tube", "sheet", "piece", "set")

_CATEGORY_LABELS = {category: category.value.title() for category in SupplyCategory}


class SupplyFormDialog(QDialog):
    """A modal form for creating or editing a single supply."""

    def __init__(
        self, *, existing: SupplyRead | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._existing = existing
        self._color_hex: str | None = None
        self.setWindowTitle("Edit Supply" if existing else "Add Supply")
        self.setMinimumWidth(440)

        outer = QVBoxLayout(self)

        self._error_label = QLabel()
        self._error_label.setStyleSheet(f"color: {PALETTE.danger};")
        self._error_label.hide()
        outer.addWidget(self._error_label)

        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
        outer.addLayout(form)

        self._category_combo = QComboBox()
        for category, label in _CATEGORY_LABELS.items():
            self._category_combo.addItem(label, category)
        form.addRow("Category", self._category_combo)

        self._brand_edit = QLineEdit()
        self._brand_edit.setPlaceholderText("e.g. Mr. Color")
        form.addRow("Brand*", self._brand_edit)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. Gundam Gray")
        form.addRow("Name*", self._name_edit)

        self._color_name_edit = QLineEdit()
        self._color_name_edit.setPlaceholderText("e.g. Gundam Gray, Flat White")
        form.addRow("Color name", self._color_name_edit)

        color_row = QHBoxLayout()
        self._color_swatch = QLabel()
        self._color_swatch.setFixedSize(24, 24)
        self._color_swatch.setStyleSheet(
            f"background-color: transparent; border: 1px solid {PALETTE.border}; "
            "border-radius: 4px;"
        )
        color_row.addWidget(self._color_swatch)
        pick_color_button = QPushButton("Pick Color…")
        pick_color_button.clicked.connect(self._on_pick_color)
        color_row.addWidget(pick_color_button)
        clear_color_button = QPushButton("Clear")
        clear_color_button.clicked.connect(self._on_clear_color)
        color_row.addWidget(clear_color_button)
        color_row.addStretch(1)
        form.addRow("Color swatch", color_row)

        self._quantity_spin = QDoubleSpinBox()
        self._quantity_spin.setRange(0, 10_000)
        self._quantity_spin.setDecimals(1)
        form.addRow("Quantity on hand", self._quantity_spin)

        self._unit_combo = QComboBox()
        self._unit_combo.setEditable(True)
        self._unit_combo.addItems(_UNITS)
        form.addRow("Unit", self._unit_combo)

        self._low_stock_spin = QDoubleSpinBox()
        self._low_stock_spin.setRange(0, 10_000)
        self._low_stock_spin.setDecimals(1)
        self._low_stock_spin.setSpecialValueText("Not tracked")
        form.addRow("Low stock threshold", self._low_stock_spin)

        self._purchase_date_edit = QDateEdit()
        self._purchase_date_edit.setCalendarPopup(True)
        self._purchase_date_edit.setSpecialValueText("Not set")
        self._purchase_date_edit.setDate(self._purchase_date_edit.minimumDate())
        form.addRow("Purchase date", self._purchase_date_edit)

        self._purchase_price_spin = QDoubleSpinBox()
        self._purchase_price_spin.setRange(0, 100_000)
        self._purchase_price_spin.setDecimals(2)
        self._purchase_price_spin.setPrefix("$")
        form.addRow("Purchase price", self._purchase_price_spin)

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

        self._result_data: SupplyCreate | None = None
        if existing is not None:
            self._populate_from(existing)

    def _populate_from(self, supply: SupplyRead) -> None:
        index = self._category_combo.findData(SupplyCategory(supply.category))
        if index >= 0:
            self._category_combo.setCurrentIndex(index)
        self._brand_edit.setText(supply.brand)
        self._name_edit.setText(supply.name)
        self._color_name_edit.setText(supply.color_name or "")
        self._set_color_hex(supply.color_hex)
        self._quantity_spin.setValue(supply.quantity_on_hand)
        self._unit_combo.setCurrentText(supply.unit)
        self._low_stock_spin.setValue(supply.low_stock_threshold or 0)
        if supply.purchase_date is not None:
            purchase_date = supply.purchase_date
            self._purchase_date_edit.setDate(
                QDate(purchase_date.year, purchase_date.month, purchase_date.day)
            )
        self._purchase_price_spin.setValue((supply.purchase_price_cents or 0) / 100)
        self._tags_edit.setText(", ".join(supply.tags))
        self._notes_edit.setPlainText(supply.notes or "")

    def _on_pick_color(self) -> None:
        initial = QColor(self._color_hex) if self._color_hex else QColor(PALETTE.surface_raised)
        chosen = QColorDialog.getColor(initial, self, "Pick a Color")
        if chosen.isValid():
            self._set_color_hex(chosen.name())

    def _on_clear_color(self) -> None:
        self._set_color_hex(None)

    def _set_color_hex(self, color_hex: str | None) -> None:
        self._color_hex = color_hex
        swatch_color = color_hex or "transparent"
        self._color_swatch.setStyleSheet(
            f"background-color: {swatch_color}; border: 1px solid {PALETTE.border}; "
            "border-radius: 4px;"
        )

    def _on_accept(self) -> None:
        brand = self._brand_edit.text().strip()
        name = self._name_edit.text().strip()

        if not brand or not name:
            self._error_label.setText("Brand and name are required.")
            self._error_label.show()
            return

        purchase_date: date | None = None
        if self._purchase_date_edit.date() != self._purchase_date_edit.minimumDate():
            python_date = self._purchase_date_edit.date().toPython()
            assert isinstance(python_date, date)
            purchase_date = python_date

        self._result_data = SupplyCreate(
            category=self._category_combo.currentData(),
            brand=brand,
            name=name,
            color_name=self._color_name_edit.text().strip() or None,
            color_hex=self._color_hex,
            quantity_on_hand=self._quantity_spin.value(),
            unit=self._unit_combo.currentText().strip() or "bottle",
            low_stock_threshold=self._low_stock_spin.value() or None,
            purchase_date=purchase_date,
            purchase_price_cents=round(self._purchase_price_spin.value() * 100) or None,
            tags=[tag.strip() for tag in self._tags_edit.text().split(",") if tag.strip()],
            notes=self._notes_edit.toPlainText().strip() or None,
        )
        self.accept()

    def result_data(self) -> SupplyCreate | None:
        """The validated form data, populated only after a successful accept."""
        return self._result_data
