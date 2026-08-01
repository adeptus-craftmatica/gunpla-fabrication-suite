"""A small dashboard widget summarizing how many items are on the wishlist."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from gunpla_fabrication_suite.plugins.wishlist.services.wishlist_service import WishlistService
from gunpla_fabrication_suite.shared_ui import set_label_role


class WishlistCountWidget(QWidget):
    """Shows how many items are still wanted (not archived, not purchased)."""

    def __init__(self, service: WishlistService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)

        count = service.count_active_items()
        count_label = QLabel(str(count))
        set_label_role(count_label, "big-number")
        layout.addWidget(count_label)

        caption = QLabel("item" if count == 1 else "items")
        set_label_role(caption, "secondary")
        layout.addWidget(caption)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
