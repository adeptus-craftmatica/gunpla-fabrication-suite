"""The live work-session timer: start/pause/resume/stop for one build.

Only one timer can run at a time across the whole application (enforced by
:class:`~gunpla_fabrication_suite.plugins.build_planner.services.work_session_service.WorkSessionService`);
this widget shows a clear, non-blocking notice when the running timer
belongs to a different build instead of silently doing nothing.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from gunpla_fabrication_suite.core.notifications import NotificationCenter, NotificationSeverity
from gunpla_fabrication_suite.plugins.build_planner.errors import WorkSessionAlreadyRunningError
from gunpla_fabrication_suite.plugins.build_planner.services.work_session_service import (
    WorkSessionService,
)
from gunpla_fabrication_suite.plugins.build_planner.ui.session_dialogs import StopSessionDialog
from gunpla_fabrication_suite.shared_ui import set_label_role


def _format_duration(total_seconds: int) -> str:
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


class TimerWidget(QWidget):
    """Shows this build's timer state and lets the user control it."""

    def __init__(
        self,
        work_session_service: WorkSessionService,
        build_id: str,
        notifications: NotificationCenter,
        *,
        on_changed: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = work_session_service
        self._build_id = build_id
        self._notifications = notifications
        self._on_changed = on_changed

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._status_label = QLabel()
        set_label_role(self._status_label, "secondary")
        layout.addWidget(self._status_label)

        self._elapsed_label = QLabel("00:00:00")
        self._elapsed_label.setStyleSheet("font-size: 28px; font-weight: 700;")
        layout.addWidget(self._elapsed_label)

        button_row = QHBoxLayout()
        self._start_button = QPushButton("Start Timer")
        self._start_button.clicked.connect(self._on_start)
        button_row.addWidget(self._start_button)

        self._pause_resume_button = QPushButton("Pause")
        self._pause_resume_button.clicked.connect(self._on_pause_resume)
        button_row.addWidget(self._pause_resume_button)

        self._stop_button = QPushButton("Stop")
        self._stop_button.clicked.connect(self._on_stop)
        button_row.addWidget(self._stop_button)

        button_row.addStretch(1)
        layout.addLayout(button_row)

        self._ticker = QTimer(self)
        self._ticker.setInterval(1000)
        self._ticker.timeout.connect(self._tick)

        self.refresh()

    def refresh(self) -> None:
        """Re-check the globally active session and update the display."""
        active = self._service.get_active_session()

        if active is None:
            self._status_label.setText("No timer running.")
            self._elapsed_label.setText("00:00:00")
            self._set_buttons(start=True, pause_resume=False, stop=False)
            self._ticker.stop()
            return

        if active.build_project_id != self._build_id:
            self._status_label.setText("A timer is running on a different build.")
            self._elapsed_label.setText(_format_duration(active.elapsed_seconds))
            self._set_buttons(start=False, pause_resume=False, stop=False)
            self._ticker.stop()
            return

        self._elapsed_label.setText(_format_duration(active.elapsed_seconds))
        if active.is_paused:
            self._status_label.setText("Paused.")
            self._pause_resume_button.setText("Resume")
            self._ticker.stop()
        else:
            self._status_label.setText("Running.")
            self._pause_resume_button.setText("Pause")
            self._ticker.start()
        self._set_buttons(start=False, pause_resume=True, stop=True)

    def _set_buttons(self, *, start: bool, pause_resume: bool, stop: bool) -> None:
        self._start_button.setEnabled(start)
        self._pause_resume_button.setEnabled(pause_resume)
        self._stop_button.setEnabled(stop)

    def _tick(self) -> None:
        active = self._service.get_active_session()
        if active is not None and active.build_project_id == self._build_id:
            self._elapsed_label.setText(_format_duration(active.elapsed_seconds))

    def _on_start(self) -> None:
        try:
            self._service.start_timer(self._build_id)
        except WorkSessionAlreadyRunningError:
            self._notifications.post(
                "A timer is already running on another build.",
                severity=NotificationSeverity.WARNING,
                source="build_planner",
            )
        self.refresh()
        self._on_changed()

    def _on_pause_resume(self) -> None:
        active = self._service.get_active_session()
        if active is None:
            return
        if active.is_paused:
            self._service.resume_timer(active.id)
        else:
            self._service.pause_timer(active.id)
        self.refresh()
        self._on_changed()

    def _on_stop(self) -> None:
        active = self._service.get_active_session()
        if active is None:
            return
        dialog = StopSessionDialog(parent=self)
        if dialog.exec() == StopSessionDialog.DialogCode.Accepted:
            result = dialog.result_data()
            self._service.stop_timer(
                active.id,
                notes=cast(str | None, result["notes"]),
                is_billable=cast(bool, result["is_billable"]),
                rating=cast(int | None, result["rating"]),
            )
            self._notifications.post(
                "Work session logged.",
                severity=NotificationSeverity.SUCCESS,
                source="build_planner",
            )
        self.refresh()
        self._on_changed()
