"""The build journal: a quick add-note form plus a newest-first feed."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from gunpla_fabrication_suite.plugins.build_planner.schemas import JournalEntryCreate
from gunpla_fabrication_suite.plugins.build_planner.services.journal_service import JournalService
from gunpla_fabrication_suite.shared_ui import EmptyStateWidget
from gunpla_fabrication_suite.themes import PALETTE


class JournalWidget(QWidget):
    """Lets the user add a quick note and see the build's journal feed."""

    def __init__(
        self, journal_service: JournalService, build_id: str, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._service = journal_service
        self._build_id = build_id

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QLabel("Build Journal")
        header.setStyleSheet("font-weight: 600;")
        layout.addWidget(header)

        entry_row = QHBoxLayout()
        self._note_edit = QPlainTextEdit()
        self._note_edit.setPlaceholderText("What happened in this session?")
        self._note_edit.setFixedHeight(60)
        entry_row.addWidget(self._note_edit, stretch=1)

        add_button = QPushButton("Add Entry")
        add_button.clicked.connect(self._on_add)
        entry_row.addWidget(add_button)
        layout.addLayout(entry_row)

        self._feed_layout = QVBoxLayout()
        layout.addLayout(self._feed_layout)
        layout.addStretch(1)

        self.refresh()

    def refresh(self) -> None:
        """Reload the journal feed from the database."""
        while self._feed_layout.count():
            item = self._feed_layout.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()

        entries = self._service.list_entries(self._build_id)
        if not entries:
            self._feed_layout.addWidget(
                EmptyStateWidget(
                    title="No journal entries yet",
                    description="Log what you did right after a session, while it's fresh.",
                )
            )
            return

        for entry in entries:
            timestamp = entry.created_at.strftime("%b %d, %Y  %H:%M")
            entry_label = QLabel(f"{timestamp}\n{entry.note}")
            entry_label.setWordWrap(True)
            entry_label.setStyleSheet(
                f"padding: 8px; background-color: {PALETTE.surface}; "
                f"border: 1px solid {PALETTE.border}; border-radius: 4px;"
            )
            self._feed_layout.addWidget(entry_label)

    def _on_add(self) -> None:
        note = self._note_edit.toPlainText().strip()
        if not note:
            return
        self._service.add_entry(self._build_id, JournalEntryCreate(note=note))
        self._note_edit.clear()
        self.refresh()
