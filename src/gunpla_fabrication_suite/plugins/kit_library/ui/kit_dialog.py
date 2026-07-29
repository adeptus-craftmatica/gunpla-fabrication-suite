"""The add/edit kit dialog."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
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

from gunpla_fabrication_suite.plugins.kit_library.models.kit import CollectionStatus
from gunpla_fabrication_suite.plugins.kit_library.schemas import KitCreate, KitRead
from gunpla_fabrication_suite.themes import PALETTE

_GRADES = ("HG", "MG", "RG", "PG", "SD", "RE/100", "FM", "Other")

_STATUS_LABELS = {status: status.value.replace("_", " ").title() for status in CollectionStatus}


class KitFormDialog(QDialog):
    """A modal form for creating or editing a single kit."""

    def __init__(self, *, existing: KitRead | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._existing = existing
        self.setWindowTitle("Edit Kit" if existing else "Add Kit")
        self.setMinimumWidth(440)

        outer = QVBoxLayout(self)

        self._error_label = QLabel()
        self._error_label.setStyleSheet(f"color: {PALETTE.danger};")
        self._error_label.hide()
        outer.addWidget(self._error_label)

        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
        outer.addLayout(form)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. RX-78-2 Gundam")
        form.addRow("Kit name*", self._name_edit)

        self._manufacturer_edit = QLineEdit()
        self._manufacturer_edit.setPlaceholderText("e.g. Bandai")
        form.addRow("Manufacturer*", self._manufacturer_edit)

        self._grade_combo = QComboBox()
        self._grade_combo.setEditable(True)
        self._grade_combo.addItems(_GRADES)
        form.addRow("Grade*", self._grade_combo)

        self._scale_edit = QLineEdit()
        self._scale_edit.setPlaceholderText("e.g. 1/144")
        form.addRow("Scale", self._scale_edit)

        self._designation_edit = QLineEdit()
        self._designation_edit.setPlaceholderText("e.g. RX-78-2")
        form.addRow("MS designation", self._designation_edit)

        self._product_number_edit = QLineEdit()
        form.addRow("Product number", self._product_number_edit)

        self._series_edit = QLineEdit()
        self._series_edit.setPlaceholderText("e.g. Mobile Suit Gundam")
        form.addRow("Series", self._series_edit)

        self._release_year_spin = QSpinBox()
        self._release_year_spin.setRange(0, 2100)
        self._release_year_spin.setSpecialValueText("Unknown")
        form.addRow("Release year", self._release_year_spin)

        self._status_combo = QComboBox()
        for status, label in _STATUS_LABELS.items():
            self._status_combo.addItem(label, status)
        form.addRow("Status", self._status_combo)

        self._priority_spin = QSpinBox()
        self._priority_spin.setRange(0, 5)
        form.addRow("Priority (0-5)", self._priority_spin)

        self._difficulty_spin = QSpinBox()
        self._difficulty_spin.setRange(0, 5)
        self._difficulty_spin.setSpecialValueText("Unrated")
        form.addRow("Difficulty (1-5)", self._difficulty_spin)

        self._estimated_hours_spin = QDoubleSpinBox()
        self._estimated_hours_spin.setRange(0, 500)
        self._estimated_hours_spin.setDecimals(1)
        self._estimated_hours_spin.setSuffix(" hrs")
        form.addRow("Estimated build time", self._estimated_hours_spin)

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

        self._storage_location_edit = QLineEdit()
        form.addRow("Storage location", self._storage_location_edit)

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

        self._result_data: KitCreate | None = None
        if existing is not None:
            self._populate_from(existing)

    def _populate_from(self, kit: KitRead) -> None:
        self._name_edit.setText(kit.name)
        self._manufacturer_edit.setText(kit.manufacturer)
        self._grade_combo.setCurrentText(kit.grade)
        self._scale_edit.setText(kit.scale or "")
        self._designation_edit.setText(kit.mobile_suit_designation or "")
        self._product_number_edit.setText(kit.product_number or "")
        self._series_edit.setText(kit.series or "")
        self._release_year_spin.setValue(kit.release_year or 0)
        index = self._status_combo.findData(CollectionStatus(kit.status))
        if index >= 0:
            self._status_combo.setCurrentIndex(index)
        self._priority_spin.setValue(kit.priority)
        self._difficulty_spin.setValue(kit.difficulty_estimate or 0)
        self._estimated_hours_spin.setValue(kit.estimated_build_hours or 0)
        if kit.purchase_date is not None:
            purchase_date = kit.purchase_date
            self._purchase_date_edit.setDate(
                QDate(purchase_date.year, purchase_date.month, purchase_date.day)
            )
        self._purchase_price_spin.setValue((kit.purchase_price_cents or 0) / 100)
        self._storage_location_edit.setText(kit.storage_location or "")
        self._tags_edit.setText(", ".join(kit.tags))
        self._notes_edit.setPlainText(kit.notes or "")

    def _on_accept(self) -> None:
        name = self._name_edit.text().strip()
        manufacturer = self._manufacturer_edit.text().strip()
        grade = self._grade_combo.currentText().strip()

        if not name or not manufacturer or not grade:
            self._error_label.setText("Kit name, manufacturer, and grade are required.")
            self._error_label.show()
            return

        purchase_date: date | None = None
        if self._purchase_date_edit.date() != self._purchase_date_edit.minimumDate():
            python_date = self._purchase_date_edit.date().toPython()
            assert isinstance(python_date, date)
            purchase_date = python_date

        self._result_data = KitCreate(
            manufacturer=manufacturer,
            name=name,
            grade=grade,
            scale=self._scale_edit.text().strip() or None,
            mobile_suit_designation=self._designation_edit.text().strip() or None,
            product_number=self._product_number_edit.text().strip() or None,
            series=self._series_edit.text().strip() or None,
            release_year=self._release_year_spin.value() or None,
            status=self._status_combo.currentData(),
            priority=self._priority_spin.value(),
            difficulty_estimate=self._difficulty_spin.value() or None,
            estimated_build_hours=self._estimated_hours_spin.value() or None,
            purchase_date=purchase_date,
            purchase_price_cents=round(self._purchase_price_spin.value() * 100) or None,
            storage_location=self._storage_location_edit.text().strip() or None,
            tags=[tag.strip() for tag in self._tags_edit.text().split(",") if tag.strip()],
            notes=self._notes_edit.toPlainText().strip() or None,
        )
        self.accept()

    def result_data(self) -> KitCreate | None:
        """The validated form data, populated only after a successful accept."""
        return self._result_data
