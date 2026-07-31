"""A consistent page title block, shared by every top-level page."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from gunpla_fabrication_suite.shared_ui.labels import set_label_role
from gunpla_fabrication_suite.shared_ui.tokens import PAGE_TITLE, SPACING


class PageHeader(QWidget):
    """The title (and optional back-link, subtitle, and actions) every page starts with.

    ``title_label`` is a public attribute so a page whose title isn't known
    until later — a detail view loading its record — can update it after
    construction with ``header.title_label.setText(...)`` instead of needing
    a bespoke setter method.
    """

    def __init__(
        self,
        title: str,
        *,
        subtitle: str = "",
        leading: QWidget | None = None,
        actions: list[QWidget] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(SPACING.xs)

        if leading is not None:
            leading_row = QHBoxLayout()
            leading_row.setContentsMargins(0, 0, 0, 0)
            leading_row.addWidget(leading)
            leading_row.addStretch(1)
            outer.addLayout(leading_row)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(SPACING.sm)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(PAGE_TITLE)
        title_row.addWidget(self.title_label)
        title_row.addStretch(1)

        for action in actions or []:
            title_row.addWidget(action)

        outer.addLayout(title_row)

        self.subtitle_label: QLabel | None = None
        if subtitle:
            self.subtitle_label = QLabel(subtitle)
            set_label_role(self.subtitle_label, "secondary")
            outer.addWidget(self.subtitle_label)
