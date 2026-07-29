"""Renders whatever pages are currently in the :class:`NavigationRegistry`."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QPushButton, QVBoxLayout, QWidget

from gunpla_fabrication_suite.plugin_sdk.registries import NavigationRegistry
from gunpla_fabrication_suite.themes import PALETTE


class NavigationRail(QWidget):
    """A vertical list of navigation buttons, one per registered page."""

    page_selected = Signal(str)

    def __init__(self, registry: NavigationRegistry, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("navigationRail")
        self.setStyleSheet(
            f"#navigationRail {{ background-color: {PALETTE.surface}; "
            f"border-right: 1px solid {PALETTE.border}; }}"
        )
        self.setFixedWidth(200)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 12, 8, 12)
        self._layout.setSpacing(2)
        self._layout.addStretch(1)

        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}

        self.refresh(registry)

    def refresh(self, registry: NavigationRegistry) -> None:
        """Rebuild the rail's buttons from the registry's current contributions."""
        for button in self._buttons.values():
            self._button_group.removeButton(button)
        self._buttons.clear()

        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                # setParent(None) detaches it from rendering immediately;
                # deleteLater() alone leaves it visible until the event loop
                # processes the deletion, which can briefly double-render if
                # refresh() runs again before that happens.
                widget.setParent(None)
                widget.deleteLater()

        for index, page in enumerate(registry.all_pages()):
            button = QPushButton(page.title)
            if page.icon is not None:
                button.setIcon(page.icon)
            button.setCheckable(True)
            button.setFlat(True)
            button.setStyleSheet(
                "QPushButton { text-align: left; padding: 8px 10px; "
                "border: none; border-radius: 4px; }"
                f"QPushButton:checked {{ background-color: {PALETTE.surface_raised}; "
                f"border-left: 3px solid {PALETTE.accent}; }}"
                f"QPushButton:hover {{ background-color: {PALETTE.surface_raised}; }}"
            )
            button.setAccessibleName(page.title)
            button.clicked.connect(
                lambda _checked, page_id=page.page_id: self.page_selected.emit(page_id)
            )
            self._button_group.addButton(button)
            self._buttons[page.page_id] = button
            self._layout.insertWidget(index, button)

        if self._buttons:
            first_button = next(iter(self._buttons.values()))
            first_button.setChecked(True)

    def select(self, page_id: str) -> None:
        """Programmatically mark ``page_id`` as the active button, if present."""
        button = self._buttons.get(page_id)
        if button is not None:
            button.setChecked(True)
