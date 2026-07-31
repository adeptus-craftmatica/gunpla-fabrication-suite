"""A reusable, generic inspector panel shown on the right edge of the shell.

Any page can push a details widget into the inspector's "Details" tab; the
"Activity", "Attachments", "Notes", and "History" tabs are structurally
present for every record type but only populated once the plugins that own
those concepts (build journal, photography, ...) are implemented.

Lives in ``shared_ui`` (not ``shell.widgets``, where it originated) because
it is threaded into plugins via ``PluginContext`` — a page needs a live
reference to push details into it — and ``plugin_sdk`` cannot import from
``shell`` without a circular import (``shell`` already imports from
``plugin_sdk``).
"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QTabWidget, QVBoxLayout, QWidget

from gunpla_fabrication_suite.shared_ui.labels import set_label_role


class InspectorPanel(QWidget):
    """The right-hand inspector: contextual details for the current selection."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Background/border come from the #inspectorPanel rule in
        # themes/base.py's global stylesheet, so they stay correct across a
        # live theme switch.
        self.setObjectName("inspectorPanel")
        # No fixed width: Rail and Command Deck collapse this panel to 0 by
        # default (see main_window.py's _apply_default_splitter_sizes) since
        # most pages don't push anything into it yet; Workbench gives it a
        # real default width instead, since that's its whole point.

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        self._details_container = QWidget()
        self._details_layout = QVBoxLayout(self._details_container)
        self._details_layout.setContentsMargins(12, 12, 12, 12)
        self._show_empty_details()

        self._tabs.addTab(self._details_container, "Details")
        self._tabs.addTab(self._empty_tab("No activity yet."), "Activity")
        self._tabs.addTab(self._empty_tab("No attachments yet."), "Attachments")
        self._tabs.addTab(self._empty_tab("No notes yet."), "Notes")
        self._tabs.addTab(self._empty_tab("No history yet."), "History")

    def _empty_tab(self, message: str) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        label = QLabel(message)
        set_label_role(label, "secondary")
        label.setStyleSheet("padding: 12px;")
        label.setWordWrap(True)
        layout.addWidget(label)
        layout.addStretch(1)
        return tab

    def _show_empty_details(self) -> None:
        while self._details_layout.count():
            item = self._details_layout.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                # setParent(None) detaches it from rendering immediately;
                # deleteLater() alone would leave it visible until the event
                # loop processes the deletion.
                widget.setParent(None)
                widget.deleteLater()
        label = QLabel("Nothing selected.")
        set_label_role(label, "secondary")
        self._details_layout.addWidget(label)
        self._details_layout.addStretch(1)

    def set_details_widget(self, widget: QWidget | None) -> None:
        """Replace the Details tab's content with ``widget``, or clear it if ``None``."""
        while self._details_layout.count():
            item = self._details_layout.takeAt(0)
            existing_widget = item.widget() if item is not None else None
            if existing_widget is not None:
                existing_widget.setParent(None)
                existing_widget.deleteLater()

        if widget is None:
            self._show_empty_details()
            return

        self._details_layout.addWidget(widget)
