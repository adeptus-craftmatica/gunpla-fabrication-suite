"""The About page: current version, a manual update check, and its startup toggle."""

from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QCheckBox, QLabel, QPushButton, QVBoxLayout, QWidget

from gunpla_fabrication_suite import __version__
from gunpla_fabrication_suite.core.jobs import BackgroundJobManager
from gunpla_fabrication_suite.core.notifications import NotificationCenter
from gunpla_fabrication_suite.core.settings import SettingsService
from gunpla_fabrication_suite.core.update_check import check_for_update_now, parse_version
from gunpla_fabrication_suite.shared_ui import Card, PageHeader


class AboutPage(QWidget):
    """Shows the running version and lets the user check for updates, on demand or at startup."""

    def __init__(
        self,
        settings_service: SettingsService,
        jobs: BackgroundJobManager,
        notifications: NotificationCenter,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings_service = settings_service
        self._jobs = jobs
        self._notifications = notifications

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(16)

        outer.addWidget(
            PageHeader(
                "About",
                subtitle="Version information and update checks.",
            )
        )

        version_card = Card("Gunpla Fabrication Suite")
        self._version_label = QLabel(f"Version {__version__}")
        version_card.add_widget(self._version_label)

        self._status_label = QLabel()
        version_card.add_widget(self._status_label)

        self._view_release_button = QPushButton("View Release")
        self._view_release_button.clicked.connect(self._on_view_release_clicked)
        version_card.add_widget(self._view_release_button)

        self._check_button = QPushButton("Check for Updates")
        self._check_button.clicked.connect(self._on_check_clicked)
        version_card.add_widget(self._check_button)

        outer.addWidget(version_card)

        auto_check_card = Card("Automatic Checks")
        update_check = settings_service.current.update_check
        self._auto_check_checkbox = QCheckBox("Check for updates on startup")
        self._auto_check_checkbox.setChecked(update_check.enabled)
        self._auto_check_checkbox.toggled.connect(self._on_auto_check_toggled)
        auto_check_card.add_widget(self._auto_check_checkbox)
        outer.addWidget(auto_check_card)

        outer.addStretch(1)

        self._refresh_status()

    def _refresh_status(self) -> None:
        update_check = self._settings_service.current.update_check
        latest = update_check.last_known_version
        latest_parsed = parse_version(latest) if latest is not None else None
        current_parsed = parse_version(__version__)
        has_update = (
            latest_parsed is not None
            and current_parsed is not None
            and latest_parsed > current_parsed
        )

        if update_check.last_checked_at is None:
            self._status_label.setText("Never checked for updates.")
        elif has_update:
            self._status_label.setText(f"Version {latest} is available.")
        else:
            self._status_label.setText("You're running the latest version.")

        self._view_release_button.setVisible(has_update)
        self._release_url = (
            f"https://github.com/adeptus-craftmatica/gunpla-fabrication-suite/releases/tag/v{latest}"
            if has_update
            else None
        )

    def _on_view_release_clicked(self) -> None:
        if self._release_url is not None:
            QDesktopServices.openUrl(QUrl(self._release_url))

    def _on_check_clicked(self) -> None:
        self._check_button.setEnabled(False)
        self._check_button.setText("Checking…")

        handle = check_for_update_now(
            self._settings_service, self._jobs, self._notifications, __version__
        )

        def _reset_button(job_id: str, _payload: object) -> None:
            if job_id != handle.id:
                return
            self._check_button.setEnabled(True)
            self._check_button.setText("Check for Updates")
            self._refresh_status()
            self._jobs.job_succeeded.disconnect(_reset_button)
            self._jobs.job_failed.disconnect(_reset_button_failed)

        def _reset_button_failed(job_id: str, _error: str) -> None:
            if job_id != handle.id:
                return
            self._check_button.setEnabled(True)
            self._check_button.setText("Check for Updates")
            self._refresh_status()
            self._jobs.job_succeeded.disconnect(_reset_button)
            self._jobs.job_failed.disconnect(_reset_button_failed)

        self._jobs.job_succeeded.connect(_reset_button)
        self._jobs.job_failed.connect(_reset_button_failed)

    def _on_auto_check_toggled(self, checked: bool) -> None:
        settings = self._settings_service.current
        settings.update_check.enabled = checked
        self._settings_service.save(settings)
