"""The build detail workspace: header, progress, stages/tasks, timer, and journal."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gunpla_fabrication_suite.core.notifications import NotificationCenter, NotificationSeverity
from gunpla_fabrication_suite.plugins.build_planner.errors import BuildNotFoundError
from gunpla_fabrication_suite.plugins.build_planner.models.enums import BuildStatus
from gunpla_fabrication_suite.plugins.build_planner.schemas import BuildProjectRead
from gunpla_fabrication_suite.plugins.build_planner.services.build_service import BuildService
from gunpla_fabrication_suite.plugins.build_planner.services.journal_service import JournalService
from gunpla_fabrication_suite.plugins.build_planner.services.work_session_service import (
    WorkSessionService,
)
from gunpla_fabrication_suite.plugins.build_planner.ui.edit_dialogs import EditBuildDetailsDialog
from gunpla_fabrication_suite.plugins.build_planner.ui.journal_widget import JournalWidget
from gunpla_fabrication_suite.plugins.build_planner.ui.stage_tree_widget import StageTreeWidget
from gunpla_fabrication_suite.plugins.build_planner.ui.timer_widget import TimerWidget
from gunpla_fabrication_suite.plugins.kit_library.services.kit_service import KitService
from gunpla_fabrication_suite.shared_ui import confirm_destructive_action
from gunpla_fabrication_suite.themes import PALETTE

_STATUS_LABELS = {status: status.value.replace("_", " ").title() for status in BuildStatus}


class BuildDetailView(QWidget):
    """A single build's full workspace: progress, plan, timer, and journal."""

    def __init__(
        self,
        *,
        build_service: BuildService,
        work_session_service: WorkSessionService,
        journal_service: JournalService,
        kit_service: KitService,
        notifications: NotificationCenter,
        build_id: str,
        on_back: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._build_service = build_service
        self._work_session_service = work_session_service
        self._kit_service = kit_service
        self._notifications = notifications
        self._build_id = build_id
        self._on_back = on_back

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)

        back_button = QPushButton("← All Builds")
        back_button.setFlat(True)
        back_button.clicked.connect(self._on_back)
        outer.addWidget(back_button, alignment=Qt.AlignmentFlag.AlignLeft)

        header_row = QHBoxLayout()
        self._title_label = QLabel()
        self._title_label.setStyleSheet("font-size: 22px; font-weight: 600;")
        header_row.addWidget(self._title_label)
        header_row.addStretch(1)

        edit_button = QPushButton("Edit Details")
        edit_button.clicked.connect(self._on_edit_details)
        header_row.addWidget(edit_button)
        outer.addLayout(header_row)

        self._kit_label = QLabel()
        self._kit_label.setStyleSheet(f"color: {PALETTE.text_secondary};")
        outer.addWidget(self._kit_label)

        progress_row = QHBoxLayout()
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        progress_row.addWidget(self._progress_bar, stretch=1)
        self._progress_label = QLabel()
        progress_row.addWidget(self._progress_label)
        outer.addLayout(progress_row)

        self._status_label = QLabel()
        outer.addWidget(self._status_label)

        self._actions_row = QHBoxLayout()
        outer.addLayout(self._actions_row)

        splitter = QSplitter()
        outer.addWidget(splitter, stretch=1)

        self._stage_tree = StageTreeWidget(build_service, build_id, on_changed=self._refresh_header)
        splitter.addWidget(self._stage_tree)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        self._timer_widget = TimerWidget(
            work_session_service, build_id, notifications, on_changed=self._on_timer_changed
        )
        right_layout.addWidget(self._timer_widget)

        sessions_label = QLabel("Recent Sessions")
        sessions_label.setStyleSheet("font-weight: 600; margin-top: 8px;")
        right_layout.addWidget(sessions_label)

        self._sessions_table = QTableWidget(0, 3)
        self._sessions_table.setHorizontalHeaderLabels(["Started", "Duration", "Notes"])
        self._sessions_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self._sessions_table.verticalHeader().setVisible(False)
        self._sessions_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._sessions_table.setMaximumHeight(160)
        right_layout.addWidget(self._sessions_table)

        self._journal_widget = JournalWidget(journal_service, build_id)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self._journal_widget)
        right_layout.addWidget(scroll_area, stretch=1)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        self.refresh()

    def refresh(self) -> None:
        """Reload everything from the database."""
        try:
            build = self._build_service.get_build(self._build_id)
        except BuildNotFoundError:
            self._on_back()
            return

        self._current_build = build
        self._title_label.setText(build.title)

        try:
            kit = self._kit_service.get_kit(build.kit_id)
            self._kit_label.setText(f"{kit.manufacturer} — {kit.name} ({kit.grade})")
        except Exception:
            self._kit_label.setText("Kit unavailable")

        self._progress_bar.setValue(build.progress_percent)
        override_note = " (manual override)" if build.is_progress_overridden else ""
        self._progress_label.setText(f"{build.progress_percent}%{override_note}")

        status_label = _STATUS_LABELS.get(BuildStatus(build.status), build.status)
        commission_note = " · Commission" if build.is_commission else ""
        self._status_label.setText(f"Status: {status_label}{commission_note}")

        self._refresh_actions(build)
        self._stage_tree.refresh()
        self._timer_widget.refresh()
        self._refresh_sessions_table()
        self._journal_widget.refresh()

    def _refresh_header(self) -> None:
        self.refresh()

    def _on_timer_changed(self) -> None:
        self.refresh()

    def _refresh_actions(self, build: BuildProjectRead) -> None:
        while self._actions_row.count():
            item = self._actions_row.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                # setParent(None) detaches it from rendering immediately;
                # deleteLater() alone leaves it visible until the event loop
                # processes the deletion, which can briefly double-render if
                # refresh() runs again before that happens.
                widget.setParent(None)
                widget.deleteLater()

        status = BuildStatus(build.status)

        if status == BuildStatus.PLANNING:
            self._add_action("Start Build", self._on_start)
        if status in (BuildStatus.PAUSED, BuildStatus.WAITING_ON_SUPPLIES):
            self._add_action("Resume Build", self._on_resume)
        if status == BuildStatus.IN_PROGRESS:
            self._add_action("Pause Build", self._on_pause)
        if status != BuildStatus.COMPLETED and not build.is_deleted:
            self._add_action("Mark Completed", self._on_mark_completed)
        if not build.is_deleted:
            self._add_action("Archive", self._on_archive)
        else:
            self._add_action("Restore", self._on_restore)

        self._actions_row.addStretch(1)

    def _add_action(self, label: str, callback: Callable[[], None]) -> None:
        button = QPushButton(label)
        button.clicked.connect(callback)
        self._actions_row.addWidget(button)

    def _refresh_sessions_table(self) -> None:
        sessions = self._work_session_service.list_sessions(self._build_id)
        finished = [s for s in sessions if not s.is_running][:10]
        self._sessions_table.setRowCount(len(finished))
        for row, session in enumerate(finished):
            started = session.started_at.strftime("%b %d, %H:%M")
            hours, remainder = divmod(session.elapsed_seconds, 3600)
            minutes = remainder // 60
            duration = f"{hours}h {minutes}m"
            self._sessions_table.setItem(row, 0, QTableWidgetItem(started))
            self._sessions_table.setItem(row, 1, QTableWidgetItem(duration))
            self._sessions_table.setItem(row, 2, QTableWidgetItem(session.notes or ""))

    def _on_edit_details(self) -> None:
        dialog = EditBuildDetailsDialog(self._current_build, parent=self)
        accepted = dialog.exec() == EditBuildDetailsDialog.DialogCode.Accepted
        result = dialog.result_data()
        if accepted and result is not None:
            title, notes = result
            self._build_service.update_details(self._build_id, title=title, notes=notes)
            self.refresh()

    def _on_start(self) -> None:
        self._build_service.start_build(self._build_id)
        self.refresh()

    def _on_pause(self) -> None:
        self._build_service.pause_build(self._build_id)
        self.refresh()

    def _on_resume(self) -> None:
        self._build_service.resume_build(self._build_id)
        self.refresh()

    def _on_mark_completed(self) -> None:
        self._build_service.mark_completed(self._build_id)
        self._notifications.post(
            "Build marked completed. Nice work!",
            severity=NotificationSeverity.SUCCESS,
            source="build_planner",
        )
        self.refresh()

    def _on_archive(self) -> None:
        if not confirm_destructive_action(
            self,
            title="Archive build",
            message="Archive this build? It will be hidden from the active list until restored.",
            confirm_label="Archive",
        ):
            return
        self._build_service.archive_build(self._build_id)
        self._on_back()

    def _on_restore(self) -> None:
        self._build_service.restore_build(self._build_id)
        self.refresh()
