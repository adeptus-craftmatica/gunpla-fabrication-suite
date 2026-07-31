"""The dashboard page: renders whatever widgets other plugins have contributed."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QGridLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from gunpla_fabrication_suite.core.layout import COMMAND_DECK, LayoutManager
from gunpla_fabrication_suite.plugin_sdk.registries import DashboardWidgetRegistry
from gunpla_fabrication_suite.shared_ui import Card, EmptyStateWidget, PageHeader, set_button_kind

_RAIL_COLUMNS = 3
_COMMAND_DECK_COLUMNS = 5


class DashboardPage(QWidget):
    """The dashboard: a header, a refresh action, and a grid of plugin widgets.

    The grid's column count responds to the active layout — Command Deck
    has no left nav rail eating into the width, so it uses that extra room
    for more columns instead of leaving it as dead space.
    """

    def __init__(
        self,
        registry: DashboardWidgetRegistry,
        layout_manager: LayoutManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._registry = registry
        self._layout_manager = layout_manager

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(16)

        refresh_button = QPushButton("Refresh")
        set_button_kind(refresh_button, "secondary")
        refresh_button.clicked.connect(self._rebuild)
        outer.addWidget(
            PageHeader(
                "Dashboard", subtitle="Your workshop, at a glance.", actions=[refresh_button]
            )
        )

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setStyleSheet("QScrollArea { border: none; }")
        outer.addWidget(self._scroll_area, stretch=1)

        layout_manager.layout_changed.connect(self._on_layout_changed)
        self._rebuild()

    def _on_layout_changed(self, _layout_id: str) -> None:
        self._rebuild()

    def _columns(self) -> int:
        if self._layout_manager.current == COMMAND_DECK:
            return _COMMAND_DECK_COLUMNS
        return _RAIL_COLUMNS

    def _rebuild(self) -> None:
        contributions = self._registry.all_widgets()

        if not contributions:
            self._scroll_area.setWidget(
                EmptyStateWidget(
                    title="No dashboard widgets yet",
                    description="Widgets appear here as plugins contribute them — "
                    "for example, once the Kit Library has kits in your collection.",
                )
            )
            return

        columns = self._columns()
        content = QWidget()
        grid = QGridLayout(content)
        grid.setSpacing(12)

        row = 0
        for index, contribution in enumerate(contributions):
            card = self._build_card(contribution.title, contribution.factory())
            row = index // columns
            grid.addWidget(card, row, index % columns)

        grid.setRowStretch(row + 1, 1)
        self._scroll_area.setWidget(content)

    def _build_card(self, title: str, content_widget: QWidget) -> QWidget:
        card = Card(title)
        card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        card.add_widget(content_widget)
        return card
