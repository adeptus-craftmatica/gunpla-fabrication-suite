"""Dialogs for stopping a timer and for logging a session retroactively."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from PySide6.QtCore import QDate, QDateTime, QTime
from PySide6.QtWidgets import (
    QCheckBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


def _to_qdatetime(value: datetime) -> QDateTime:
    return QDateTime(
        QDate(value.year, value.month, value.day),
        QTime(value.hour, value.minute, value.second),
    )


def _from_qdatetime(value: QDateTime) -> datetime:
    date = value.date()
    time = value.time()
    return datetime(
        date.year(), date.month(), date.day(), time.hour(), time.minute(), time.second(), tzinfo=UTC
    )


class StopSessionDialog(QDialog):
    """Collects optional notes/billing details when a timer stops."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Stop Timer")
        self.setMinimumWidth(360)

        outer = QVBoxLayout(self)
        form = QFormLayout()
        outer.addLayout(form)

        self._notes_edit = QPlainTextEdit()
        self._notes_edit.setFixedHeight(70)
        self._notes_edit.setPlaceholderText("What did you work on?")
        form.addRow("Notes", self._notes_edit)

        self._rating_spin = QSpinBox()
        self._rating_spin.setRange(0, 5)
        self._rating_spin.setSpecialValueText("Unrated")
        form.addRow("Session rating (1-5)", self._rating_spin)

        self._billable_checkbox = QCheckBox("Billable")
        form.addRow("", self._billable_checkbox)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def result_data(self) -> dict[str, object]:
        """The entered notes/rating/billable flag."""
        return {
            "notes": self._notes_edit.toPlainText().strip() or None,
            "rating": self._rating_spin.value() or None,
            "is_billable": self._billable_checkbox.isChecked(),
        }


class ManualSessionDialog(QDialog):
    """Logs a completed work session retroactively (no live timer)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Log Manual Session")
        self.setMinimumWidth(380)

        outer = QVBoxLayout(self)
        form = QFormLayout()
        outer.addLayout(form)

        now = datetime.now(UTC)

        self._start_edit = QDateTimeEdit()
        self._start_edit.setCalendarPopup(True)
        self._start_edit.setDateTime(_to_qdatetime(now - timedelta(hours=1)))
        form.addRow("Started", self._start_edit)

        self._end_edit = QDateTimeEdit()
        self._end_edit.setCalendarPopup(True)
        self._end_edit.setDateTime(_to_qdatetime(now))
        form.addRow("Ended", self._end_edit)

        self._notes_edit = QPlainTextEdit()
        self._notes_edit.setFixedHeight(70)
        form.addRow("Notes", self._notes_edit)

        self._billable_checkbox = QCheckBox("Billable")
        form.addRow("", self._billable_checkbox)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

        self._result: dict[str, object] | None = None

    def _on_accept(self) -> None:
        start = _from_qdatetime(self._start_edit.dateTime())
        end = _from_qdatetime(self._end_edit.dateTime())
        if end <= start:
            return
        self._result = {
            "started_at": start,
            "ended_at": end,
            "notes": self._notes_edit.toPlainText().strip() or None,
            "is_billable": self._billable_checkbox.isChecked(),
        }
        self.accept()

    def result_data(self) -> dict[str, object] | None:
        """The entered session data, populated only after a successful accept."""
        return self._result
