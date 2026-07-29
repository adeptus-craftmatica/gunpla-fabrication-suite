"""The dashboard page: renders whatever widgets other plugins have contributed."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from gunpla_fabrication_suite.plugin_sdk.registries import DashboardWidgetRegistry
from gunpla_fabrication_suite.shared_ui import EmptyStateWidget
from gunpla_fabrication_suite.themes import PALETTE

_COLUMNS = 3


class DashboardPage(QWidget):
    """The dashboard: a header, a refresh action, and a grid of plugin widgets."""

    def __init__(self, registry: DashboardWidgetRegistry, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._registry = registry

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(16)

        header_row = QHBoxLayout()
        title = QLabel("Dashboard")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        header_row.addWidget(title)
        header_row.addStretch(1)

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self._rebuild)
        header_row.addWidget(refresh_button)
        outer.addLayout(header_row)

        subtitle = QLabel("Your workshop, at a glance.")
        subtitle.setStyleSheet(f"color: {PALETTE.text_secondary};")
        outer.addWidget(subtitle)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setStyleSheet("QScrollArea { border: none; }")
        outer.addWidget(self._scroll_area, stretch=1)

        self._rebuild()

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

        content = QWidget()
        grid = QGridLayout(content)
        grid.setSpacing(12)

        row = 0
        for index, contribution in enumerate(contributions):
            card = self._build_card(contribution.title, contribution.factory())
            row = index // _COLUMNS
            grid.addWidget(card, row, index % _COLUMNS)

        grid.setRowStretch(row + 1, 1)
        self._scroll_area.setWidget(content)

    def _build_card(self, title: str, content_widget: QWidget) -> QWidget:
        card = QWidget()
        card.setObjectName("dashboardCard")
        card.setStyleSheet(
            f"#dashboardCard {{ background-color: {PALETTE.surface}; "
            f"border: 1px solid {PALETTE.border}; border-radius: 6px; }}"
        )
        card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 16)

        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"color: {PALETTE.text_secondary}; font-weight: 600; border: none;"
        )
        layout.addWidget(title_label)
        layout.addWidget(content_widget)
        return card
