"""A reusable, framed content container with consistent padding and depth."""

from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QLabel, QVBoxLayout, QWidget

from gunpla_fabrication_suite.shared_ui.labels import set_label_role
from gunpla_fabrication_suite.shared_ui.tokens import SPACING


class Card(QFrame):
    """A framed section with a soft drop shadow, wrapping one piece of page content.

    Without this, tables/trees/grids float directly on the raw window
    background with nothing visually containing them. Every ``Card`` gets
    its own fresh :class:`QGraphicsDropShadowEffect` instance — sharing one
    effect object across widgets silently reparents it to only the last one.
    The frame's background/border come from the ``#card`` rule in
    ``themes/base.py``'s global stylesheet (not a local override), so it
    stays correct across a live theme switch; only the shadow color is a
    fixed literal, since shadows don't need to be theme-colored.
    """

    def __init__(self, title: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 90))
        self.setGraphicsEffect(shadow)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(SPACING.lg, SPACING.md, SPACING.lg, SPACING.lg)
        self._layout.setSpacing(SPACING.sm)

        if title:
            title_label = QLabel(title)
            set_label_role(title_label, "section-title")
            self._layout.addWidget(title_label)

    def add_widget(self, widget: QWidget, stretch: int = 0) -> None:
        """Add a widget to the card's body, below the optional title."""
        self._layout.addWidget(widget, stretch)
