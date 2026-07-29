"""A small dashboard widget summarizing the active kit count."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from gunpla_fabrication_suite.plugins.kit_library.services.kit_service import KitService
from gunpla_fabrication_suite.themes import PALETTE


class BacklogCountWidget(QWidget):
    """Shows how many kits are currently active (not archived)."""

    def __init__(self, service: KitService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)

        count = service.count_active_kits()
        count_label = QLabel(str(count))
        count_label.setStyleSheet("font-size: 32px; font-weight: 700; border: none;")
        layout.addWidget(count_label)

        caption = QLabel("kit" if count == 1 else "kits")
        caption.setStyleSheet(f"color: {PALETTE.text_secondary}; border: none;")
        layout.addWidget(caption)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
