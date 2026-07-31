"""The bottom status bar: database, background jobs, notifications, plugin health.

Every status segment pairs an icon glyph with a text label so state is never
communicated by color alone.
"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QStatusBar, QWidget

from gunpla_fabrication_suite.core.jobs import BackgroundJobManager
from gunpla_fabrication_suite.core.notifications import Notification, NotificationCenter
from gunpla_fabrication_suite.core.plugins import PluginManager, PluginStatus


def _set_status(label: QLabel, status: str | None) -> None:
    """Set the ``status`` property driving ``#statusSegment[status="..."]`` in the stylesheet."""
    label.setProperty("status", status)
    label.style().unpolish(label)
    label.style().polish(label)


class AppStatusBar(QStatusBar):
    """A persistent status bar summarizing database, job, notification, and plugin state."""

    def __init__(
        self,
        *,
        jobs: BackgroundJobManager,
        notifications: NotificationCenter,
        plugin_manager: PluginManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._jobs = jobs
        self._notifications = notifications
        self._plugin_manager = plugin_manager
        self._notification_count = 0

        self._database_label = self._make_segment()
        self._jobs_label = self._make_segment()
        self._notifications_label = self._make_segment()
        self._plugin_health_label = self._make_segment()

        for label in (
            self._database_label,
            self._jobs_label,
            self._notifications_label,
            self._plugin_health_label,
        ):
            self.addPermanentWidget(label)

        jobs.job_progress.connect(self._on_job_progress)
        jobs.job_succeeded.connect(lambda *_: self._refresh_jobs())
        jobs.job_failed.connect(lambda *_: self._refresh_jobs())
        notifications.notification_posted.connect(self._on_notification)

        self.set_database_status(ok=True)
        self._refresh_jobs()
        self._refresh_notifications()
        self.refresh_plugin_health()

    def _make_segment(self) -> QLabel:
        label = QLabel()
        # Colors come from the #statusSegment rules in themes/base.py's
        # global stylesheet, so they stay correct across a live theme
        # switch — see _set_status().
        label.setObjectName("statusSegment")
        return label

    def set_database_status(self, *, ok: bool) -> None:
        """Update the database segment. Pass ``ok=False`` after a failed integrity check."""
        symbol = "●" if ok else "✕"
        text = "Database: OK" if ok else "Database: ERROR"
        self._database_label.setText(f"{symbol} {text}")
        _set_status(self._database_label, "ok" if ok else "error")
        self._database_label.setToolTip("SQLite integrity check result")

    def _refresh_jobs(self) -> None:
        active = sum(1 for job in self._jobs.active_jobs() if job.status.value == "running")
        self._jobs_label.setText(f"⚙ Jobs: {active}")
        self._jobs_label.setToolTip("Active background jobs")

    def _on_job_progress(self, _job_id: str, _percent: int, _message: str) -> None:
        self._refresh_jobs()

    def _refresh_notifications(self) -> None:
        self._notifications_label.setText(f"🔔 Notifications: {self._notification_count}")
        self._notifications_label.setToolTip("Notifications posted this session")

    def _on_notification(self, _notification: Notification) -> None:
        self._notification_count += 1
        self._refresh_notifications()

    def refresh_plugin_health(self) -> None:
        """Recompute the plugin-health segment from the plugin manager's current records."""
        records = self._plugin_manager.records
        started = sum(1 for r in records if r.status == PluginStatus.STARTED)
        failed = sum(1 for r in records if r.status == PluginStatus.FAILED)
        if failed:
            self._plugin_health_label.setText(
                f"⚠ Plugins: {started}/{len(records)} ({failed} failed)"
            )
            _set_status(self._plugin_health_label, "warning")
        else:
            self._plugin_health_label.setText(f"● Plugins: {started}/{len(records)}")
            _set_status(self._plugin_health_label, "ok")
        self._plugin_health_label.setToolTip("Started plugins / total discovered")
