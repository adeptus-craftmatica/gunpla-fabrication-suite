"""Small modal dialogs for editing a build's, stage's, or task's details."""

from __future__ import annotations

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from gunpla_fabrication_suite.plugins.build_planner.schemas import (
    BuildProjectRead,
    BuildStageRead,
    BuildTaskRead,
)


class EditStageDialog(QDialog):
    """Edit a stage's name and progress weight."""

    def __init__(self, stage: BuildStageRead, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Stage")
        self.setMinimumWidth(360)

        outer = QVBoxLayout(self)
        form = QFormLayout()
        outer.addLayout(form)

        self._name_edit = QLineEdit(stage.name)
        form.addRow("Name*", self._name_edit)

        self._weight_spin = QSpinBox()
        self._weight_spin.setRange(1, 1000)
        self._weight_spin.setValue(stage.weight)
        form.addRow("Weight", self._weight_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

        self._name: str | None = None
        self._weight: int | None = None

    def _on_accept(self) -> None:
        name = self._name_edit.text().strip()
        if not name:
            return
        self._name = name
        self._weight = self._weight_spin.value()
        self.accept()

    def result_data(self) -> tuple[str, int] | None:
        """The edited ``(name, weight)``, populated only after a successful accept."""
        if self._name is None or self._weight is None:
            return None
        return self._name, self._weight


class EditTaskDialog(QDialog):
    """Edit a task's title, due date, estimated/actual hours, and notes."""

    def __init__(self, task: BuildTaskRead, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Task")
        self.setMinimumWidth(380)

        outer = QVBoxLayout(self)
        form = QFormLayout()
        outer.addLayout(form)

        self._title_edit = QLineEdit(task.title)
        form.addRow("Title*", self._title_edit)

        self._due_date_edit = QDateEdit()
        self._due_date_edit.setCalendarPopup(True)
        self._due_date_edit.setSpecialValueText("Not set")
        if task.due_date is not None:
            due = task.due_date
            self._due_date_edit.setDate(QDate(due.year, due.month, due.day))
        else:
            self._due_date_edit.setDate(self._due_date_edit.minimumDate())
        form.addRow("Due date", self._due_date_edit)

        self._estimated_hours_spin = QDoubleSpinBox()
        self._estimated_hours_spin.setRange(0, 500)
        self._estimated_hours_spin.setDecimals(1)
        self._estimated_hours_spin.setValue(task.estimated_hours or 0)
        form.addRow("Estimated hours", self._estimated_hours_spin)

        self._actual_hours_spin = QDoubleSpinBox()
        self._actual_hours_spin.setRange(0, 500)
        self._actual_hours_spin.setDecimals(1)
        self._actual_hours_spin.setValue(task.actual_hours or 0)
        form.addRow("Actual hours", self._actual_hours_spin)

        self._notes_edit = QPlainTextEdit(task.notes or "")
        self._notes_edit.setFixedHeight(70)
        form.addRow("Notes", self._notes_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

        self._result: dict[str, object] | None = None

    def _on_accept(self) -> None:
        title = self._title_edit.text().strip()
        if not title:
            return

        due_date = None
        if self._due_date_edit.date() != self._due_date_edit.minimumDate():
            due_date = self._due_date_edit.date().toPython()

        self._result = {
            "title": title,
            "due_date": due_date,
            "estimated_hours": self._estimated_hours_spin.value() or None,
            "actual_hours": self._actual_hours_spin.value() or None,
            "notes": self._notes_edit.toPlainText().strip() or None,
        }
        self.accept()

    def result_data(self) -> dict[str, object] | None:
        """The edited field values, populated only after a successful accept."""
        return self._result


class EditBuildDetailsDialog(QDialog):
    """Edit a build's title and free-text notes."""

    def __init__(self, build: BuildProjectRead, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Build Details")
        self.setMinimumWidth(400)

        outer = QVBoxLayout(self)
        form = QFormLayout()
        outer.addLayout(form)

        self._title_edit = QLineEdit(build.title)
        form.addRow("Title*", self._title_edit)

        self._notes_edit = QPlainTextEdit(build.notes or "")
        self._notes_edit.setFixedHeight(100)
        form.addRow("Notes", self._notes_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

        self._result: tuple[str, str | None] | None = None

    def _on_accept(self) -> None:
        title = self._title_edit.text().strip()
        if not title:
            return
        self._result = (title, self._notes_edit.toPlainText().strip() or None)
        self.accept()

    def result_data(self) -> tuple[str, str | None] | None:
        """The edited ``(title, notes)``, populated only after a successful accept."""
        return self._result
