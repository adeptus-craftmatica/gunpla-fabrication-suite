"""The build detail workspace: header, progress, stages/tasks, timer, and journal."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from gunpla_fabrication_suite.core.jobs import BackgroundJobManager
from gunpla_fabrication_suite.core.layout import COMMAND_DECK, LayoutManager
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
from gunpla_fabrication_suite.plugins.photography.models.entity_types import PhotoEntityType
from gunpla_fabrication_suite.plugins.photography.services.photo_service import PhotoService
from gunpla_fabrication_suite.plugins.photography.ui.photo_gallery_widget import PhotoGalleryWidget
from gunpla_fabrication_suite.shared_ui import (
    SPACING,
    ButtonKind,
    Card,
    PageHeader,
    configure_table_columns,
    confirm_destructive_action,
    set_button_kind,
    set_label_role,
)

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
        photo_service: PhotoService,
        jobs: BackgroundJobManager,
        notifications: NotificationCenter,
        layout_manager: LayoutManager,
        build_id: str,
        on_back: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._build_service = build_service
        self._work_session_service = work_session_service
        self._kit_service = kit_service
        self._notifications = notifications
        self._layout_manager = layout_manager
        self._build_id = build_id
        self._on_back = on_back

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)

        back_button = QPushButton("← All Builds")
        set_button_kind(back_button, "ghost")
        back_button.clicked.connect(self._on_back)

        edit_button = QPushButton("Edit Details")
        set_button_kind(edit_button, "secondary")
        edit_button.clicked.connect(self._on_edit_details)

        self._header = PageHeader("", leading=back_button, actions=[edit_button])
        self._title_label = self._header.title_label
        outer.addWidget(self._header)

        self._kit_label = QLabel()
        set_label_role(self._kit_label, "secondary")
        outer.addWidget(self._kit_label)

        progress_row = QHBoxLayout()
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setTextVisible(False)  # _progress_label shows the % instead
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
        stage_card = Card()
        stage_card.add_widget(self._stage_tree, stretch=1)
        splitter.addWidget(stage_card)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self._timer_widget = TimerWidget(
            work_session_service, build_id, notifications, on_changed=self._on_timer_changed
        )
        timer_card = Card()
        timer_card.add_widget(self._timer_widget)

        sessions_label = QLabel("Recent Sessions")
        set_label_role(sessions_label, "section-title")
        timer_card.add_widget(sessions_label)

        self._sessions_table = QTableWidget(0, 3)
        self._sessions_table.setHorizontalHeaderLabels(["Started", "Duration", "Notes"])
        self._sessions_table.verticalHeader().setVisible(False)
        self._sessions_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._sessions_table.setMaximumHeight(160)
        timer_card.add_widget(self._sessions_table)
        right_layout.addWidget(timer_card)

        self._journal_widget = JournalWidget(journal_service, build_id)
        self._journal_scroll = QScrollArea()
        self._journal_scroll.setWidgetResizable(True)
        self._journal_scroll.setWidget(self._journal_widget)

        self._photo_gallery = PhotoGalleryWidget(
            photo_service=photo_service,
            jobs=jobs,
            notifications=notifications,
            entity_type=PhotoEntityType.BUILD.value,
            entity_id=build_id,
        )

        self._right_layout = right_layout
        self._journal_photos_section: QWidget | None = None
        self._rebuild_journal_photos_section()

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        layout_manager.layout_changed.connect(self._on_layout_changed)
        self.refresh()

    def _on_layout_changed(self, _layout_id: str) -> None:
        self._rebuild_journal_photos_section()

    def _rebuild_journal_photos_section(self) -> None:
        old_section = self._journal_photos_section
        if old_section is not None:
            self._right_layout.removeWidget(old_section)
            old_section.setParent(None)
            old_section.deleteLater()

        if self._layout_manager.current == COMMAND_DECK:
            # Command Deck's extra width has no tab bar competing for
            # attention, so Journal and Photos are both always visible,
            # stacked, instead of hidden behind tabs.
            section: QWidget = QWidget()
            section_layout = QVBoxLayout(section)
            section_layout.setContentsMargins(0, 0, 0, 0)
            section_layout.setSpacing(SPACING.sm)

            journal_card = Card("Journal")
            journal_card.add_widget(self._journal_scroll, stretch=1)
            section_layout.addWidget(journal_card, 1)

            photos_card = Card("Photos")
            photos_card.add_widget(self._photo_gallery, stretch=1)
            section_layout.addWidget(photos_card, 1)
        else:
            tabs = QTabWidget()
            tabs.addTab(self._journal_scroll, "Journal")
            tabs.addTab(self._photo_gallery, "Photos")
            section = Card()
            section.add_widget(tabs, stretch=1)

        self._journal_photos_section = section
        self._right_layout.addWidget(section, 1)
        # Tearing down the old section's setParent(None) hide()-cascades down
        # to these two reused, live widgets, explicitly marking them hidden —
        # reparenting them into the new section doesn't clear that flag, so
        # they must be shown again explicitly or they render as empty space.
        self._journal_scroll.show()
        self._photo_gallery.show()

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
        self._photo_gallery.refresh()

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
            self._add_action("Start Build", self._on_start, "primary")
        if status in (BuildStatus.PAUSED, BuildStatus.WAITING_ON_SUPPLIES):
            self._add_action("Resume Build", self._on_resume, "primary")
        if status == BuildStatus.IN_PROGRESS:
            self._add_action("Pause Build", self._on_pause, "secondary")
        if status != BuildStatus.COMPLETED and not build.is_deleted:
            self._add_action("Mark Completed", self._on_mark_completed, "secondary")
        if not build.is_deleted:
            self._add_action("Archive", self._on_archive, "danger")
        else:
            self._add_action("Restore", self._on_restore, "secondary")

        self._actions_row.addStretch(1)

    def _add_action(self, label: str, callback: Callable[[], None], kind: ButtonKind) -> None:
        button = QPushButton(label)
        set_button_kind(button, kind)
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
        configure_table_columns(self._sessions_table, stretch_column=2)

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
