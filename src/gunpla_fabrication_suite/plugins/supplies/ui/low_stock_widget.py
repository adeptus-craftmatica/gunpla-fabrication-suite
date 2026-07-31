"""A small dashboard widget summarizing how many supplies are running low."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from gunpla_fabrication_suite.plugins.supplies.services.supply_service import SupplyService
from gunpla_fabrication_suite.themes import PALETTE


class LowStockWidget(QWidget):
    """Shows how many supplies are at or below their low-stock threshold."""

    def __init__(self, service: SupplyService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)

        count = service.count_low_stock_supplies()
        count_label = QLabel(str(count))
        color = PALETTE.warning if count else PALETTE.text_primary
        count_label.setStyleSheet(
            f"font-size: 32px; font-weight: 700; border: none; color: {color};"
        )
        layout.addWidget(count_label)

        caption = QLabel("running low")
        caption.setStyleSheet(f"color: {PALETTE.text_secondary}; border: none;")
        layout.addWidget(caption)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
