"""A reusable empty-state placeholder for lists, tables, and galleries with no data."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QFontMetrics, QResizeEvent
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from gunpla_fabrication_suite.shared_ui.buttons import set_button_kind
from gunpla_fabrication_suite.shared_ui.labels import set_label_role

_DESCRIPTION_MAX_WIDTH = 360
_DESCRIPTION_MIN_WIDTH = 120
_DESCRIPTION_SIDE_MARGIN = 40


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
        self._description_label: QLabel | None = None

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # No color override: inherits the theme's primary text color already.
        title_label.setStyleSheet("font-size: 16px; font-weight: 600;")
        layout.addWidget(title_label)

        if description:
            description_label = QLabel(description)
            description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            description_label.setWordWrap(True)
            set_label_role(description_label, "secondary")
            layout.addWidget(description_label)
            self._description_label = description_label
            # QLabel's own wordWrap height-for-width resolution turned out to
            # be unreliable once nested inside a QScrollArea — it can settle
            # on a height that's shorter than the text actually needs and
            # never self-correct, clipping the wrapped text top and bottom.
            # Computing the exact wrapped height ourselves with QFontMetrics,
            # and fixing both width and height explicitly, sidesteps that
            # layout-convergence question entirely. See shared_ui/toast.py
            # for the sibling fix (a fixed *width* is enough there because
            # that label always renders at one guaranteed width).
            self._resize_description_label()

        if action_label and on_action is not None:
            action_button = QPushButton(action_label)
            set_button_kind(action_button, "primary")
            action_button.clicked.connect(on_action)
            layout.addWidget(action_button, alignment=Qt.AlignmentFlag.AlignCenter)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._resize_description_label()

    def _resize_description_label(self) -> None:
        label = self._description_label
        if label is None:
            return

        available = self.width() - _DESCRIPTION_SIDE_MARGIN
        width = max(_DESCRIPTION_MIN_WIDTH, min(available, _DESCRIPTION_MAX_WIDTH))

        metrics = QFontMetrics(label.font())
        bounding_rect = metrics.boundingRect(
            QRect(0, 0, width, 0), int(Qt.TextFlag.TextWordWrap), label.text()
        )

        label.setFixedWidth(width)
        label.setFixedHeight(bounding_rect.height() + 4)
