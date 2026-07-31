"""A fuzzy-filterable list of every registered command, launched with Ctrl+K."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from gunpla_fabrication_suite.plugin_sdk.contracts import CommandContribution
from gunpla_fabrication_suite.plugin_sdk.registries import CommandRegistry
from gunpla_fabrication_suite.shared_ui import fuzzy_score
from gunpla_fabrication_suite.themes import PALETTE


class CommandPaletteDialog(QWidget):
    """A frameless, centered overlay listing commands that match the typed filter."""

    def __init__(self, registry: CommandRegistry, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Popup)
        self.setFixedSize(480, 360)
        self.setStyleSheet(
            f"background-color: {PALETTE.surface_raised}; border: 1px solid {PALETTE.border};"
        )
        self._registry = registry

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Type a command…")
        self._search_box.textChanged.connect(self._refresh_results)
        layout.addWidget(self._search_box)

        self._results = QListWidget()
        self._results.itemActivated.connect(self._run_selected)
        layout.addWidget(self._results)

        self._search_box.setFocus()
        self._refresh_results("")

    def _refresh_results(self, query: str) -> None:
        self._results.clear()
        scored: list[tuple[int, CommandContribution]] = []
        for command in self._registry.all_commands():
            score = fuzzy_score(query, command.title)
            if score is not None:
                scored.append((score, command))
        scored.sort(key=lambda pair: pair[0])

        for _score, command in scored:
            label = command.title
            if command.shortcut:
                label = f"{label}    {command.shortcut}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, command)
            self._results.addItem(item)

        if self._results.count():
            self._results.setCurrentRow(0)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        if event.key() == Qt.Key.Key_Return:
            self._run_selected(self._results.currentItem())
            return
        if event.key() == Qt.Key.Key_Down:
            next_row = min(self._results.currentRow() + 1, self._results.count() - 1)
            self._results.setCurrentRow(next_row)
            return
        if event.key() == Qt.Key.Key_Up:
            self._results.setCurrentRow(max(self._results.currentRow() - 1, 0))
            return
        super().keyPressEvent(event)

    def _run_selected(self, item: QListWidgetItem | None) -> None:
        if item is None:
            return
        command: CommandContribution = item.data(Qt.ItemDataRole.UserRole)
        self.close()
        command.callback()
