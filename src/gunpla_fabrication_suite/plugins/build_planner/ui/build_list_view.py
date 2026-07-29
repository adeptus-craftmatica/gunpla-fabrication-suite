"""The build list: a table view and a status-grouped Kanban view.

Kanban cards are click-to-open, not drag-and-drop — status changes happen
through the explicit action buttons in the build detail view instead. See
``stage_tree_widget.py`` for the same "explicit actions over drag-and-drop"
decision applied to stage reordering.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedLayout,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gunpla_fabrication_suite.plugins.build_planner.models.enums import BuildStatus
from gunpla_fabrication_suite.plugins.build_planner.schemas import BuildProjectRead
from gunpla_fabrication_suite.plugins.build_planner.services.build_service import BuildService
from gunpla_fabrication_suite.plugins.build_planner.ui.new_build_dialog import NewBuildDialog
from gunpla_fabrication_suite.plugins.kit_library.services.kit_service import KitService
from gunpla_fabrication_suite.shared_ui import EmptyStateWidget
from gunpla_fabrication_suite.themes import PALETTE

_TABLE_COLUMNS = ("Title", "Status", "Progress", "Commission")
_KANBAN_COLUMNS = (
    BuildStatus.PLANNING,
    BuildStatus.IN_PROGRESS,
    BuildStatus.PAUSED,
    BuildStatus.WAITING_ON_SUPPLIES,
    BuildStatus.COMPLETED,
)


class BuildListView(QWidget):
    """Lists builds as a table or a Kanban board, and starts new ones."""

    def __init__(
        self,
        build_service: BuildService,
        kit_service: KitService,
        *,
        on_select: Callable[[str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._build_service = build_service
        self._kit_service = kit_service
        self._on_select = on_select
        self._builds: list[BuildProjectRead] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)

        header_row = QHBoxLayout()
        title = QLabel("Build Planner")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        header_row.addWidget(title)
        header_row.addStretch(1)

        new_build_button = QPushButton("New Build")
        new_build_button.setDefault(True)
        new_build_button.clicked.connect(self._on_new_build)
        header_row.addWidget(new_build_button)
        outer.addLayout(header_row)

        toolbar_row = QHBoxLayout()
        self._kanban_checkbox = QCheckBox("Kanban view")
        self._kanban_checkbox.toggled.connect(self._refresh_view)
        toolbar_row.addWidget(self._kanban_checkbox)

        self._show_archived_checkbox = QCheckBox("Show archived")
        self._show_archived_checkbox.toggled.connect(self.refresh)
        toolbar_row.addWidget(self._show_archived_checkbox)
        toolbar_row.addStretch(1)
        outer.addLayout(toolbar_row)

        self._stack = QStackedLayout()
        outer.addLayout(self._stack, stretch=1)

        self._table = QTableWidget(0, len(_TABLE_COLUMNS))
        self._table.setHorizontalHeaderLabels(_TABLE_COLUMNS)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.itemDoubleClicked.connect(self._on_table_row_activated)
        self._stack.addWidget(self._table)

        self._kanban_scroll = QScrollArea()
        self._kanban_scroll.setWidgetResizable(True)
        self._kanban_scroll.setStyleSheet("QScrollArea { border: none; }")
        self._stack.addWidget(self._kanban_scroll)

        self._empty_state = EmptyStateWidget(
            title="No builds yet",
            description="Start your first build from a kit already in your library.",
            action_label="New Build",
            on_action=self._on_new_build,
        )
        self._stack.addWidget(self._empty_state)

        self.refresh()

    def refresh(self) -> None:
        """Reload the build list from the database."""
        self._builds = self._build_service.list_builds(
            include_archived=self._show_archived_checkbox.isChecked()
        )
        self._refresh_view()

    def _refresh_view(self) -> None:
        if not self._builds:
            self._stack.setCurrentWidget(self._empty_state)
            return

        if self._kanban_checkbox.isChecked():
            self._stack.setCurrentWidget(self._kanban_scroll)
            self._build_kanban()
        else:
            self._stack.setCurrentWidget(self._table)
            self._build_table()

    def _build_table(self) -> None:
        self._table.setRowCount(len(self._builds))
        for row, build in enumerate(self._builds):
            self._set_row_item(row, 0, build.title, build)
            status_text = build.status.replace("_", " ").title()
            if build.is_deleted:
                status_text = f"Archived — {status_text}"
            self._set_row_item(row, 1, status_text, build)
            self._set_row_item(row, 2, f"{build.progress_percent}%", build)
            self._set_row_item(row, 3, "Yes" if build.is_commission else "—", build)

    def _set_row_item(self, row: int, column: int, text: str, build: BuildProjectRead) -> None:
        item = QTableWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, build.id)
        self._table.setItem(row, column, item)

    def _on_table_row_activated(self, item: QTableWidgetItem) -> None:
        build_id = item.data(Qt.ItemDataRole.UserRole)
        if build_id:
            self._on_select(build_id)

    def _build_kanban(self) -> None:
        content = QWidget()
        grid = QGridLayout(content)
        grid.setSpacing(12)

        for column, status in enumerate(_KANBAN_COLUMNS):
            column_widget = self._build_kanban_column(status)
            grid.addWidget(column_widget, 0, column)

        self._kanban_scroll.setWidget(content)

    def _build_kanban_column(self, status: BuildStatus) -> QWidget:
        column = QWidget()
        column.setObjectName("kanbanColumn")
        column.setStyleSheet(
            f"#kanbanColumn {{ background-color: {PALETTE.surface}; "
            f"border: 1px solid {PALETTE.border}; border-radius: 6px; }}"
        )
        column.setFixedWidth(220)
        layout = QVBoxLayout(column)

        label = QLabel(status.value.replace("_", " ").title())
        label.setStyleSheet(f"font-weight: 600; color: {PALETTE.text_secondary}; border: none;")
        layout.addWidget(label)

        matching = [build for build in self._builds if build.status == status.value]
        for build in matching:
            layout.addWidget(self._build_kanban_card(build))
        layout.addStretch(1)
        return column

    def _build_kanban_card(self, build: BuildProjectRead) -> QWidget:
        card = QPushButton(f"{build.title}\n{build.progress_percent}%")
        card.setStyleSheet(
            f"text-align: left; padding: 8px; background-color: {PALETTE.surface_raised}; "
            f"border: 1px solid {PALETTE.border}; border-radius: 4px;"
        )
        card.clicked.connect(lambda: self._on_select(build.id))
        return card

    def _on_new_build(self) -> None:
        dialog = NewBuildDialog(self._kit_service, parent=self)
        accepted = dialog.exec() == NewBuildDialog.DialogCode.Accepted
        data = dialog.result_data()
        if accepted and data is not None:
            build = self._build_service.create_build(data)
            self.refresh()
            self._on_select(build.id)
