"""The central workspace: a stack of pages, one shown at a time."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QStackedWidget, QWidget

from gunpla_fabrication_suite.plugin_sdk.registries import NavigationRegistry


class WorkspaceStack(QStackedWidget):
    """Hosts every navigation page's widget, showing exactly one at a time.

    Pages are built lazily via each contribution's ``factory`` the first time
    they are shown, not eagerly at registration time.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._page_indices: dict[str, int] = {}
        self._registry: NavigationRegistry | None = None

        placeholder = QLabel("Select a page from the navigation rail.")
        placeholder.setStyleSheet("padding: 24px;")
        self.addWidget(placeholder)

    def bind_registry(self, registry: NavigationRegistry) -> None:
        """Attach the navigation registry pages are built from."""
        self._registry = registry

    def show_page(self, page_id: str) -> None:
        """Show ``page_id``'s widget, constructing it on first use."""
        if page_id in self._page_indices:
            self.setCurrentIndex(self._page_indices[page_id])
            return

        if self._registry is None:
            return

        for page in self._registry.all_pages():
            if page.page_id == page_id:
                widget = page.factory()
                index = self.addWidget(widget)
                self._page_indices[page_id] = index
                self.setCurrentIndex(index)
                return
