"""The Backup & Restore page: export everything to a zip, or import one back."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from gunpla_fabrication_suite.core.backup import (
    BackupIntegrityError,
    BackupManifest,
    ImportResult,
    InvalidBackupError,
    export_backup,
    import_backup,
    validate_backup_manifest,
)
from gunpla_fabrication_suite.core.notifications import NotificationCenter, NotificationSeverity
from gunpla_fabrication_suite.core.paths import ApplicationPaths
from gunpla_fabrication_suite.core.persistence import DatabaseService
from gunpla_fabrication_suite.core.restart import restart_application
from gunpla_fabrication_suite.core.settings import SettingsService
from gunpla_fabrication_suite.shared_ui import (
    Card,
    PageHeader,
    confirm_destructive_action,
    set_button_kind,
)


class BackupRestorePage(QWidget):
    """Export the whole app's data to a single zip, or import one back."""

    def __init__(
        self,
        paths: ApplicationPaths,
        database: DatabaseService,
        notifications: NotificationCenter,
        settings_service: SettingsService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._paths = paths
        self._database = database
        self._notifications = notifications
        self._settings_service = settings_service

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(16)

        outer.addWidget(
            PageHeader(
                "Backup & Restore",
                subtitle="Export your whole collection to one file, or restore from a backup.",
            )
        )

        export_card = Card("Export Backup")
        export_label = QLabel(
            "Saves your kits, builds, photos, supplies, and settings to a single file "
            "you can store elsewhere or move to another computer."
        )
        export_label.setWordWrap(True)
        export_card.add_widget(export_label)
        self._export_button = QPushButton("Export Backup…")
        set_button_kind(self._export_button, "primary")
        self._export_button.clicked.connect(self._on_export_clicked)
        export_card.add_widget(self._export_button)
        outer.addWidget(export_card)

        auto_backup_card = Card("Automatic Backups")
        auto_backup = settings_service.current.auto_backup

        self._auto_backup_checkbox = QCheckBox("Enable automatic backups")
        self._auto_backup_checkbox.setChecked(auto_backup.enabled)
        self._auto_backup_checkbox.toggled.connect(self._on_auto_backup_toggled)
        auto_backup_card.add_widget(self._auto_backup_checkbox)

        form = QFormLayout()
        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(1, 90)
        self._interval_spin.setSuffix(" days")
        self._interval_spin.setValue(auto_backup.interval_days)
        self._interval_spin.valueChanged.connect(self._on_interval_changed)
        form.addRow("Back up every", self._interval_spin)

        self._retention_spin = QSpinBox()
        self._retention_spin.setRange(1, 50)
        self._retention_spin.setValue(auto_backup.retention_count)
        self._retention_spin.valueChanged.connect(self._on_retention_changed)
        form.addRow("Keep the last", self._retention_spin)
        form_widget = QWidget()
        form_widget.setLayout(form)
        auto_backup_card.add_widget(form_widget)

        last_run_text = (
            f"Last automatic backup: {auto_backup.last_backup_at}"
            if auto_backup.last_backup_at
            else "Last automatic backup: never yet"
        )
        self._last_run_label = QLabel(last_run_text)
        auto_backup_card.add_widget(self._last_run_label)
        outer.addWidget(auto_backup_card)

        import_card = Card("Import Backup")
        import_label = QLabel(
            "Replaces ALL current data with the contents of a backup file. A safety "
            "backup of your current data is made automatically first, and the app "
            "must restart afterward to load the imported data."
        )
        import_label.setWordWrap(True)
        import_card.add_widget(import_label)
        self._import_button = QPushButton("Import Backup…")
        set_button_kind(self._import_button, "danger")
        self._import_button.clicked.connect(self._on_import_clicked)
        import_card.add_widget(self._import_button)
        outer.addWidget(import_card)

        outer.addStretch(1)

    def _on_export_clicked(self) -> None:
        default_name = f"gunpla-backup-{datetime.now():%Y%m%dT%H%M%SZ}.zip"
        destination_str, _ = QFileDialog.getSaveFileName(
            self,
            "Export Backup",
            str(self._paths.backups_dir / default_name),
            "Gunpla Backup (*.zip)",
        )
        if not destination_str:
            return
        destination = Path(destination_str)
        if destination.suffix.lower() != ".zip":
            destination = destination.with_suffix(".zip")

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            export_backup(self._paths, destination)
        except Exception as exc:
            self._notifications.post(
                f"Export failed: {exc}", severity=NotificationSeverity.ERROR, source="backup"
            )
        else:
            self._notifications.post(
                f"Backup saved to {destination}.",
                severity=NotificationSeverity.SUCCESS,
                source="backup",
            )
        finally:
            QApplication.restoreOverrideCursor()

    def _on_auto_backup_toggled(self, checked: bool) -> None:
        settings = self._settings_service.current
        settings.auto_backup.enabled = checked
        self._settings_service.save(settings)

    def _on_interval_changed(self, value: int) -> None:
        settings = self._settings_service.current
        settings.auto_backup.interval_days = value
        self._settings_service.save(settings)

    def _on_retention_changed(self, value: int) -> None:
        settings = self._settings_service.current
        settings.auto_backup.retention_count = value
        self._settings_service.save(settings)

    def _on_import_clicked(self) -> None:
        source_str, _ = QFileDialog.getOpenFileName(
            self, "Import Backup", str(self._paths.backups_dir), "Gunpla Backup (*.zip)"
        )
        if not source_str:
            return
        source = Path(source_str)

        try:
            manifest = validate_backup_manifest(source)
        except InvalidBackupError as exc:
            QMessageBox.critical(self, "Invalid Backup", str(exc))
            return

        if not self._confirm_import(manifest):
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = import_backup(self._paths, self._database, source)
        except (InvalidBackupError, BackupIntegrityError) as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Import Failed", str(exc))
            return
        QApplication.restoreOverrideCursor()

        self._show_completion_dialog(result)

    def _confirm_import(self, manifest: BackupManifest) -> bool:
        return confirm_destructive_action(
            self,
            title="Replace All Data?",
            message=(
                f"This backup was exported {manifest.export_timestamp} from app version "
                f"{manifest.app_version}. Importing it will replace ALL current kits, "
                "builds, photos, supplies, and settings.\n\n"
                "A safety backup of your current data will be made automatically first. "
                "The app will need to restart afterward."
            ),
            confirm_label="Import & Replace",
        )

    def _show_completion_dialog(self, result: ImportResult) -> None:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Information)
        box.setWindowTitle("Import Complete")
        box.setText(
            "Your data has been replaced with the imported backup.\n\n"
            f"A safety backup of your previous data was saved to:\n{result.safety_backup_path}\n\n"
            "The app must restart to load the imported data."
        )
        restart_button = box.addButton("Restart Now", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("Restart Later", QMessageBox.ButtonRole.RejectRole)
        box.setInformativeText(
            "If Restart Now doesn't work in your environment, please quit and relaunch "
            "the app manually."
        )
        box.exec()
        if box.clickedButton() is restart_button:
            restart_application(self.window())
