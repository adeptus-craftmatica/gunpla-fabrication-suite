"""A reusable empty-state placeholder for lists, tables, and galleries with no data."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from gunpla_fabrication_suite.themes import PALETTE


class EmptyStateWidget(QWidget):
    """A centered message with an optional call-to-action button.

    Used whenever a table, gallery, or kanban view has nothing to show yet,
    instead of leaving a blank pane.
    """

    def __init__(
        self,
        *,
        title: str,
        description: str = "",
        action_label: str | None = None,
        on_action: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(
            f"font-size: 16px; font-weight: 600; color: {PALETTE.text_primary};"
        )
        layout.addWidget(title_label)

        if description:
            description_label = QLabel(description)
            description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            description_label.setWordWrap(True)
            description_label.setStyleSheet(f"color: {PALETTE.text_secondary};")
            layout.addWidget(description_label)

        if action_label and on_action is not None:
            action_button = QPushButton(action_label)
            action_button.setDefault(True)
            action_button.clicked.connect(on_action)
            layout.addWidget(action_button, alignment=Qt.AlignmentFlag.AlignCenter)
