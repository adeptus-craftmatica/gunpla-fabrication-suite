"""The "log a supply's use on this build" dialog."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from gunpla_fabrication_suite.plugins.build_planner.schemas import SupplyUsageCreate
from gunpla_fabrication_suite.plugins.supplies.schemas import SupplyRead
from gunpla_fabrication_suite.themes import PALETTE


def _supply_label(supply: SupplyRead) -> str:
    color_note = f" ({supply.color_name})" if supply.color_name else ""
    return f"{supply.brand} — {supply.name}{color_note}"


class LogSupplyUsageDialog(QDialog):
    """A modal form for logging a supply's use on the current build."""

    def __init__(self, active_supplies: list[SupplyRead], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._supplies = active_supplies
        self.setWindowTitle("Log Supply Used")
        self.setMinimumWidth(400)

        outer = QVBoxLayout(self)

        self._error_label = QLabel()
        self._error_label.setStyleSheet(f"color: {PALETTE.danger};")
        self._error_label.hide()
        outer.addWidget(self._error_label)

        form = QFormLayout()
        outer.addLayout(form)

        self._supply_combo = QComboBox()
        if self._supplies:
            for supply in self._supplies:
                self._supply_combo.addItem(_supply_label(supply), supply)
            self._supply_combo.currentIndexChanged.connect(self._on_supply_changed)
        else:
            self._supply_combo.addItem("No supplies in your library yet", None)
            self._supply_combo.setEnabled(False)
        form.addRow("Supply*", self._supply_combo)

        self._quantity_spin = QDoubleSpinBox()
        self._quantity_spin.setRange(0.1, 10_000)
        self._quantity_spin.setDecimals(1)
        self._quantity_spin.setValue(1)
        form.addRow("Quantity*", self._quantity_spin)

        self._notes_edit = QLineEdit()
        self._notes_edit.setPlaceholderText("Optional note")
        form.addRow("Notes", self._notes_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

        self._result_data: SupplyUsageCreate | None = None
        if self._supplies:
            self._on_supply_changed(0)

    def _on_supply_changed(self, index: int) -> None:
        supply: SupplyRead | None = self._supply_combo.itemData(index)
        if supply is not None:
            self._quantity_spin.setSuffix(f" {supply.unit}")

    def _on_accept(self) -> None:
        supply: SupplyRead | None = self._supply_combo.currentData()
        if supply is None:
            self._error_label.setText("Choose a supply.")
            self._error_label.show()
            return

        self._result_data = SupplyUsageCreate(
            supply_id=supply.id,
            quantity_used=self._quantity_spin.value(),
            notes=self._notes_edit.text().strip() or None,
        )
        self.accept()

    def result_data(self) -> SupplyUsageCreate | None:
        """The validated form data, populated only after a successful accept."""
        return self._result_data
