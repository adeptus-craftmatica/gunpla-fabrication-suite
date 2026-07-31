"""The Workbench layout's navigation: a narrow, icon-only vertical rail.

The counterpart to `NavigationRail` for a layout that trades text labels for
width — the freed-up space goes to a permanently-open Inspector panel
instead (see main_window.py). Same `NavigationRegistry`, same
`page_selected` signal, different shape.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QPushButton, QVBoxLayout, QWidget

from gunpla_fabrication_suite.plugin_sdk.registries import NavigationRegistry
from gunpla_fabrication_suite.shared_ui.buttons import set_button_kind

_WIDTH = 56


def _compact_label(title: str) -> str:
    """A short (1-2 letter) stand-in for a page's icon, derived from its title.

    No plugin has ever set `NavigationPageContribution.icon` — every page
    goes by its title alone — so a real per-page icon isn't available yet.
    Initials keep pages visually distinct without needing an icon asset
    pipeline; the full title is still available as a tooltip.
    """
    # Filter to words starting with a letter/digit — a bare connector like
    # "&" (as in "Stats & Insights") would otherwise become part of the
    # initials, and a lone "&" in a QPushButton's text is itself a stray
    # mnemonic marker (see rail.py/top_bar.py's escaping for the same issue).
    words = [word for word in title.split() if word[:1].isalnum()]
    if len(words) == 1:
        return words[0][:1].upper()
    return "".join(word[0].upper() for word in words[:2])


class CompactRail(QWidget):
    """A narrow vertical list of icon-only navigation buttons."""

    page_selected = Signal(str)

    def __init__(self, registry: NavigationRegistry, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Background/border come from the #compactRail rule in
        # themes/base.py's global stylesheet, so they stay correct across a
        # live theme switch.
        self.setObjectName("compactRail")
        self.setFixedWidth(_WIDTH)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 16, 8, 16)
        self._layout.setSpacing(4)
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
            button = QPushButton(_compact_label(page.title))
            if page.icon is not None:
                button.setIcon(page.icon)
            button.setCheckable(True)
            button.setFlat(True)
            button.setFixedHeight(40)
            set_button_kind(button, "nav")
            # The shared [kind="nav"] rule's padding (10px 14px) is sized for
            # Rail's full-width text buttons; at this rail's 56px width it
            # clips 2-letter labels. #compactRailButton overrides it with
            # tighter padding (an ID selector combined with an attribute
            # selector outranks the attribute selector alone).
            button.setObjectName("compactRailButton")
            button.setToolTip(page.title)
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
