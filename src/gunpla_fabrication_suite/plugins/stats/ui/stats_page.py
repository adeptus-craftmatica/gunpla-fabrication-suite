"""The Stats & Insights page: rolled-up numbers across the whole collection."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gunpla_fabrication_suite.plugins.stats.services.stats_service import StatsService
from gunpla_fabrication_suite.shared_ui import (
    Card,
    PageHeader,
    configure_table_columns,
    set_label_role,
)


def _tile(title: str, value: str) -> Card:
    card = Card()
    title_label = QLabel(title)
    set_label_role(title_label, "section-title")
    card.add_widget(title_label)
    value_label = QLabel(value)
    set_label_role(value_label, "big-number")
    card.add_widget(value_label)
    return card


class StatsPage(QWidget):
    """Rolled-up numbers across kits, builds, supplies, and photos."""

    def __init__(self, service: StatsService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = service

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh)
        outer.addWidget(PageHeader("Stats & Insights", actions=[refresh_button]))

        self._tiles_layout = QGridLayout()
        outer.addLayout(self._tiles_layout)

        self._status_table = QTableWidget(0, 2)
        self._status_table.setHorizontalHeaderLabels(["Build Status", "Count"])
        self._status_table.verticalHeader().setVisible(False)
        self._status_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        status_card = Card("Builds by Status")
        status_card.add_widget(self._status_table)
        outer.addWidget(status_card)

        self._grade_table = QTableWidget(0, 2)
        self._grade_table.setHorizontalHeaderLabels(["Grade", "Count"])
        self._grade_table.verticalHeader().setVisible(False)
        self._grade_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        grade_card = Card("Kits by Grade")
        grade_card.add_widget(self._grade_table)
        outer.addWidget(grade_card)

        outer.addStretch(1)

        self.refresh()

    def refresh(self) -> None:
        """Recompute the snapshot and repopulate every tile/table."""
        snapshot = self._service.compute_snapshot()

        while self._tiles_layout.count():
            item = self._tiles_layout.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        tiles = (
            ("Total Kits Owned", str(snapshot.total_kits_owned)),
            ("Total Hours Built", f"{snapshot.total_hours_built:g}"),
            ("Total Spent", f"${snapshot.total_spent_cents / 100:.2f}"),
            ("Total Photos", str(snapshot.total_photos)),
        )
        for column, (title, value) in enumerate(tiles):
            self._tiles_layout.addWidget(_tile(title, value), 0, column)

        self._status_table.setRowCount(len(snapshot.builds_by_status))
        for row, (status, count) in enumerate(sorted(snapshot.builds_by_status.items())):
            self._status_table.setItem(row, 0, QTableWidgetItem(status.replace("_", " ").title()))
            self._status_table.setItem(row, 1, QTableWidgetItem(str(count)))
        configure_table_columns(self._status_table, stretch_column=0)

        self._grade_table.setRowCount(len(snapshot.kits_by_grade))
        for row, (grade, count) in enumerate(sorted(snapshot.kits_by_grade.items())):
            self._grade_table.setItem(row, 0, QTableWidgetItem(grade))
            self._grade_table.setItem(row, 1, QTableWidgetItem(str(count)))
        configure_table_columns(self._grade_table, stretch_column=0)
