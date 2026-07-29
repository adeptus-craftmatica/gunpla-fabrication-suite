"""The stage/task editor: a checkable tree of a build's plan.

Drag-and-drop reordering is deliberately out of scope for this milestone —
stages are reordered with explicit Up/Down actions instead. This keeps the
interaction model simple and fully keyboard-accessible.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import cast

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gunpla_fabrication_suite.plugins.build_planner.schemas import BuildTaskCreate
from gunpla_fabrication_suite.plugins.build_planner.services.build_service import BuildService
from gunpla_fabrication_suite.plugins.build_planner.ui.edit_dialogs import (
    EditStageDialog,
    EditTaskDialog,
)
from gunpla_fabrication_suite.shared_ui import confirm_destructive_action

_STAGE_ROLE = Qt.ItemDataRole.UserRole
_KIND_ROLE = Qt.ItemDataRole.UserRole + 1

_COLUMNS = ("Stage / Task", "Hours", "Due")


class StageTreeWidget(QWidget):
    """A checkable tree of a build's stages and their tasks."""

    def __init__(
        self,
        build_service: BuildService,
        build_id: str,
        *,
        on_changed: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = build_service
        self._build_id = build_id
        self._on_changed = on_changed

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QHBoxLayout()
        add_stage_button = QPushButton("Add Stage")
        add_stage_button.clicked.connect(self._on_add_stage)
        toolbar.addWidget(add_stage_button)

        add_task_button = QPushButton("Add Task")
        add_task_button.clicked.connect(self._on_add_task)
        toolbar.addWidget(add_task_button)

        move_up_button = QPushButton("Move Up")
        move_up_button.clicked.connect(lambda: self._on_move_stage(-1))
        toolbar.addWidget(move_up_button)

        move_down_button = QPushButton("Move Down")
        move_down_button.clicked.connect(lambda: self._on_move_stage(1))
        toolbar.addWidget(move_down_button)

        remove_button = QPushButton("Remove")
        remove_button.clicked.connect(self._on_remove)
        toolbar.addWidget(remove_button)

        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        self._tree = QTreeWidget()
        self._tree.setColumnCount(len(_COLUMNS))
        self._tree.setHeaderLabels(list(_COLUMNS))
        self._tree.setAlternatingRowColors(True)
        self._tree.itemChanged.connect(self._on_item_changed)
        self._tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._tree)

        self.refresh()

    def refresh(self) -> None:
        """Rebuild the tree from the current stage/task data."""
        self._tree.blockSignals(True)
        try:
            self._tree.clear()
            for stage in self._service.list_stages(self._build_id):
                stage_item = QTreeWidgetItem([f"{stage.name}  (weight {stage.weight})", "", ""])
                stage_item.setFlags(stage_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                stage_item.setCheckState(
                    0, Qt.CheckState.Checked if stage.is_completed else Qt.CheckState.Unchecked
                )
                stage_item.setData(0, _STAGE_ROLE, stage.id)
                stage_item.setData(0, _KIND_ROLE, "stage")
                self._tree.addTopLevelItem(stage_item)

                for task in self._service.list_tasks(stage.id):
                    hours = f"{task.actual_hours or 0:g}/{task.estimated_hours or 0:g}"
                    due = task.due_date.isoformat() if task.due_date else ""
                    task_item = QTreeWidgetItem([task.title, hours, due])
                    task_item.setFlags(task_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    task_item.setCheckState(
                        0,
                        Qt.CheckState.Checked if task.is_completed else Qt.CheckState.Unchecked,
                    )
                    task_item.setData(0, _STAGE_ROLE, task.id)
                    task_item.setData(0, _KIND_ROLE, "task")
                    stage_item.addChild(task_item)

                stage_item.setExpanded(True)
        finally:
            self._tree.blockSignals(False)
        for column in range(len(_COLUMNS)):
            self._tree.resizeColumnToContents(column)

    def _selected_stage_id(self) -> str | None:
        item = self._tree.currentItem()
        if item is None:
            return None
        if item.data(0, _KIND_ROLE) == "stage":
            return str(item.data(0, _STAGE_ROLE))
        parent = item.parent()
        return str(parent.data(0, _STAGE_ROLE)) if parent is not None else None

    def _on_add_stage(self) -> None:
        name, accepted = QInputDialog.getText(self, "Add Stage", "Stage name:")
        if accepted and name.strip():
            self._service.add_stage(self._build_id, name.strip())
            self.refresh()
            self._on_changed()

    def _on_add_task(self) -> None:
        stage_id = self._selected_stage_id()
        if stage_id is None:
            return
        title, accepted = QInputDialog.getText(self, "Add Task", "Task title:")
        if accepted and title.strip():
            self._service.add_task(stage_id, BuildTaskCreate(title=title.strip()))
            self.refresh()
            self._on_changed()

    def _on_move_stage(self, direction: int) -> None:
        item = self._tree.currentItem()
        if item is None or item.data(0, _KIND_ROLE) != "stage":
            return
        stage_id = item.data(0, _STAGE_ROLE)
        self._service.move_stage(self._build_id, stage_id, direction=direction)
        self.refresh()
        self._on_changed()

    def _on_remove(self) -> None:
        item = self._tree.currentItem()
        if item is None:
            return
        kind = item.data(0, _KIND_ROLE)
        item_id = item.data(0, _STAGE_ROLE)

        if kind == "stage":
            if not confirm_destructive_action(
                self,
                title="Remove stage",
                message=f"Remove '{item.text(0)}' and all of its tasks?",
                confirm_label="Remove",
            ):
                return
            self._service.remove_stage(item_id)
        else:
            self._service.remove_task(item_id)

        self.refresh()
        self._on_changed()

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if column != 0:
            return
        kind = item.data(0, _KIND_ROLE)
        item_id = item.data(0, _STAGE_ROLE)
        completed = item.checkState(0) == Qt.CheckState.Checked

        if kind == "stage":
            self._service.toggle_stage_completion(item_id, completed=completed)
        else:
            self._service.toggle_task_completion(item_id, completed=completed)

        # Rebuilding the tree (refresh() calls QTreeWidget.clear()) must not
        # happen synchronously inside itemChanged — Qt is still emitting that
        # signal for `item`, and clearing the tree while it does crashes.
        # Deferring to the next event-loop iteration is the standard fix.
        QTimer.singleShot(0, self._after_item_changed)

    def _after_item_changed(self) -> None:
        self.refresh()
        self._on_changed()

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        kind = item.data(0, _KIND_ROLE)
        item_id = item.data(0, _STAGE_ROLE)

        if kind == "stage":
            stage = next(
                (s for s in self._service.list_stages(self._build_id) if s.id == item_id), None
            )
            if stage is None:
                return
            stage_dialog = EditStageDialog(stage, parent=self)
            accepted = stage_dialog.exec() == EditStageDialog.DialogCode.Accepted
            stage_result = stage_dialog.result_data()
            if accepted and stage_result is not None:
                name, weight = stage_result
                self._service.rename_stage(item_id, name=name, weight=weight)
                self.refresh()
                self._on_changed()
        else:
            parent = item.parent()
            if parent is None:
                return
            stage_id = parent.data(0, _STAGE_ROLE)
            task = next((t for t in self._service.list_tasks(stage_id) if t.id == item_id), None)
            if task is None:
                return
            task_dialog = EditTaskDialog(task, parent=self)
            accepted = task_dialog.exec() == EditTaskDialog.DialogCode.Accepted
            task_result = task_dialog.result_data()
            if accepted and task_result is not None:
                self._service.update_task_details(
                    item_id,
                    title=cast(str, task_result["title"]),
                    due_date=cast(date | None, task_result["due_date"]),
                    estimated_hours=cast(float | None, task_result["estimated_hours"]),
                    actual_hours=cast(float | None, task_result["actual_hours"]),
                    notes=cast(str | None, task_result["notes"]),
                )
                self.refresh()
                self._on_changed()
