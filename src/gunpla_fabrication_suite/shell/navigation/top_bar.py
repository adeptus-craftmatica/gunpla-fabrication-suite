"""The Command Deck layout's navigation: a horizontal bar of page buttons.

The counterpart to `NavigationRail` for a layout that reclaims the left
edge for content instead of a persistent vertical sidebar — same
`NavigationRegistry`, same `page_selected` signal, different shape.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QWidget

from gunpla_fabrication_suite.plugin_sdk.registries import NavigationRegistry
from gunpla_fabrication_suite.shared_ui.buttons import set_button_kind


class TopNavBar(QWidget):
    """A horizontal row of navigation buttons, one per registered page."""

    page_selected = Signal(str)

    def __init__(self, registry: NavigationRegistry, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Background/border come from the #topNavBar rule in
        # themes/base.py's global stylesheet, so they stay correct across a
        # live theme switch.
        self.setObjectName("topNavBar")

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(16, 8, 16, 8)
        self._layout.setSpacing(4)
        self._layout.addStretch(1)

        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}

        self.refresh(registry)

    def refresh(self, registry: NavigationRegistry) -> None:
        """Rebuild the bar's buttons from the registry's current contributions."""
        for button in self._buttons.values():
            self._button_group.removeButton(button)
        self._buttons.clear()

        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                # setParent(None) detaches it from rendering immediately;
                # deleteLater() alone leaves it visible until the event loop
                # processes the deletion.
                widget.setParent(None)
                widget.deleteLater()

        for index, page in enumerate(registry.all_pages()):
            # QPushButton treats a bare "&" as a mnemonic marker (stripped,
            # next character underlined) — escape it as "&&" so a page
            # title containing one (e.g. "Stats & Insights") renders
            # literally instead of showing a stray underline artifact.
            button = QPushButton(page.title.replace("&", "&&"))
            if page.icon is not None:
                button.setIcon(page.icon)
            button.setCheckable(True)
            button.setFlat(True)
            set_button_kind(button, "nav")
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
