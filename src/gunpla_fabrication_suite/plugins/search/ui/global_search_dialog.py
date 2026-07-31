"""A fuzzy-filterable popup searching kits, builds, photos, and supplies."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor, QKeyEvent
from PySide6.QtWidgets import QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from gunpla_fabrication_suite.core.navigation import Navigator
from gunpla_fabrication_suite.plugin_sdk.registries import NavigationRegistry
from gunpla_fabrication_suite.plugins.search.schemas import SearchResult
from gunpla_fabrication_suite.plugins.search.services.search_index_service import (
    SearchIndexService,
)
from gunpla_fabrication_suite.shared_ui import fuzzy_score
from gunpla_fabrication_suite.themes import PALETTE

_MAX_RESULTS = 30


class GlobalSearchDialog(QWidget):
    """A frameless popup listing kits/builds/photos/supplies matching the typed filter."""

    def __init__(
        self,
        index_service: SearchIndexService,
        navigation: NavigationRegistry,
        navigator: Navigator,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent, Qt.WindowType.Popup)
        self.setFixedSize(520, 400)
        self.setStyleSheet(
            f"background-color: {PALETTE.surface_raised}; border: 1px solid {PALETTE.border};"
        )
        self._navigation = navigation
        self._navigator = navigator
        self._index = index_service.build_index()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Search kits, builds, photos, supplies…")
        self._search_box.textChanged.connect(self._refresh_results)
        layout.addWidget(self._search_box)

        self._results = QListWidget()
        self._results.itemActivated.connect(self._activate)
        layout.addWidget(self._results)

        self._search_box.setFocus()
        self._refresh_results("")

    def _refresh_results(self, query: str) -> None:
        self._results.clear()
        scored: list[tuple[int, SearchResult]] = []
        for result in self._index:
            score = fuzzy_score(query, result.label)
            if score is not None:
                scored.append((score, result))
        scored.sort(key=lambda pair: pair[0])

        for _score, result in scored[:_MAX_RESULTS]:
            item = QListWidgetItem(f"{result.label}    [{result.entity_type}]")
            item.setData(Qt.ItemDataRole.UserRole, result)
            self._results.addItem(item)

        if self._results.count():
            self._results.setCurrentRow(0)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        if event.key() == Qt.Key.Key_Return:
            self._activate(self._results.currentItem())
            return
        if event.key() == Qt.Key.Key_Down:
            next_row = min(self._results.currentRow() + 1, self._results.count() - 1)
            self._results.setCurrentRow(next_row)
            return
        if event.key() == Qt.Key.Key_Up:
            self._results.setCurrentRow(max(self._results.currentRow() - 1, 0))
            return
        super().keyPressEvent(event)

    def _activate(self, item: QListWidgetItem | None) -> None:
        if item is None:
            return
        result: SearchResult = item.data(Qt.ItemDataRole.UserRole)
        self.close()

        contribution = next(
            (c for c in self._navigation.all_pages() if c.page_id == result.page_id), None
        )
        if contribution is not None and contribution.focus is not None:
            contribution.focus(result.entity_id)
        self._navigator.navigate_to(result.page_id)

    @staticmethod
    def positioned_at_cursor() -> tuple[int, int]:
        """Top-left position so the dialog opens near the cursor.

        Global Search has no ``MainWindow`` reference (unlike
        ``MainWindow._open_command_palette``, which centers against
        ``self.geometry()``) — a plugin's command callback only has
        ``PluginContext``, not the shell window.
        """
        pos = QCursor.pos()
        return pos.x() - 260, pos.y() - 40
