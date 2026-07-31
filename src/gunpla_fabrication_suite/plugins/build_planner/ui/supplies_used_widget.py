"""The build's "Supplies Used" panel: log consumption, see the running cost."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gunpla_fabrication_suite.plugins.build_planner.services.supply_usage_service import (
    SupplyUsageService,
)
from gunpla_fabrication_suite.plugins.build_planner.ui.supply_dialogs import LogSupplyUsageDialog
from gunpla_fabrication_suite.plugins.supplies.services.supply_service import (
    SupplyNotFoundError,
    SupplyService,
)
from gunpla_fabrication_suite.shared_ui import (
    configure_table_columns,
    confirm_destructive_action,
    set_label_role,
)

_COLUMNS = ("Supply", "Quantity", "Cost")


class SuppliesUsedWidget(QWidget):
    """Lists supplies logged against a build and their running total cost."""

    def __init__(
        self,
        supply_usage_service: SupplyUsageService,
        supply_service: SupplyService,
        build_id: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._usage_service = supply_usage_service
        self._supply_service = supply_service
        self._build_id = build_id

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QHBoxLayout()
        log_button = QPushButton("Log Supply")
        log_button.clicked.connect(self._on_add)
        toolbar.addWidget(log_button)

        remove_button = QPushButton("Remove")
        remove_button.clicked.connect(self._on_remove)
        toolbar.addWidget(remove_button)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(_COLUMNS)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self._table, 1)

        self._total_label = QLabel()
        set_label_role(self._total_label, "secondary")
        layout.addWidget(self._total_label)

        self._usage_ids: list[str] = []
        self.refresh()

    def refresh(self) -> None:
        """Reload logged usages and the running total from the database."""
        usages = self._usage_service.list_usages(self._build_id)
        self._usage_ids = [usage.id for usage in usages]

        self._table.setRowCount(len(usages))
        for row, usage in enumerate(usages):
            self._table.setItem(row, 0, QTableWidgetItem(self._supply_label(usage.supply_id)))
            self._table.setItem(
                row, 1, QTableWidgetItem(f"{usage.quantity_used:g} {usage.unit_snapshot}")
            )
            cost_text = (
                f"${usage.estimated_cost_cents / 100:.2f}"
                if usage.estimated_cost_cents is not None
                else "—"
            )
            self._table.setItem(row, 2, QTableWidgetItem(cost_text))
        configure_table_columns(self._table, stretch_column=0)

        total_cents = self._usage_service.total_cost_cents(self._build_id)
        self._total_label.setText(f"Total: ${total_cents / 100:.2f}")

    def _supply_label(self, supply_id: str) -> str:
        try:
            supply = self._supply_service.get_supply(supply_id)
        except SupplyNotFoundError:
            return "Unknown supply"
        color_note = f" ({supply.color_name})" if supply.color_name else ""
        return f"{supply.brand} — {supply.name}{color_note}"

    def _on_add(self) -> None:
        active_supplies = self._supply_service.list_supplies()
        dialog = LogSupplyUsageDialog(active_supplies, parent=self)
        accepted = dialog.exec() == LogSupplyUsageDialog.DialogCode.Accepted
        result = dialog.result_data()
        if accepted and result is not None:
            self._usage_service.add_usage(self._build_id, result)
            self.refresh()

    def _on_remove(self) -> None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._usage_ids):
            return
        if not confirm_destructive_action(
            self,
            title="Remove logged supply",
            message="Remove this logged usage? Its quantity will be restored to stock.",
            confirm_label="Remove",
        ):
            return
        self._usage_service.delete_usage(self._usage_ids[row])
        self.refresh()
