"""Tests for the Backup & Restore page: export/import button wiring and ordering."""

from __future__ import annotations

import pytest

from gunpla_fabrication_suite.core.backup import export_backup
from gunpla_fabrication_suite.core.notifications import NotificationCenter, NotificationSeverity
from gunpla_fabrication_suite.shell import backup_restore_page as backup_restore_page_module
from gunpla_fabrication_suite.shell.backup_restore_page import BackupRestorePage


@pytest.fixture
def notifications() -> NotificationCenter:
    return NotificationCenter()


@pytest.fixture
def page(qtbot, app_paths, database, notifications) -> BackupRestorePage:
    widget = BackupRestorePage(app_paths, database, notifications)
    qtbot.addWidget(widget)
    return widget


def test_page_constructs_with_export_and_import_buttons(page: BackupRestorePage) -> None:
    assert page._export_button.text() == "Export Backup…"
    assert page._import_button.text() == "Import Backup…"


def test_export_button_writes_a_backup_and_posts_success_toast(
    qtbot, monkeypatch, page: BackupRestorePage, app_paths, notifications, tmp_path
) -> None:
    destination = tmp_path / "manual-backup.zip"
    monkeypatch.setattr(
        backup_restore_page_module.QFileDialog,
        "getSaveFileName",
        lambda *a, **k: (str(destination), ""),
    )

    qtbot.mouseClick(page._export_button, backup_restore_page_module.Qt.MouseButton.LeftButton)

    assert destination.exists()
    assert notifications.history()[-1].severity == NotificationSeverity.SUCCESS


def test_import_button_declines_without_confirmation(
    qtbot, monkeypatch, page: BackupRestorePage, app_paths, tmp_path
) -> None:
    backup_zip = tmp_path / "backup.zip"
    export_backup(app_paths, backup_zip)

    monkeypatch.setattr(
        backup_restore_page_module.QFileDialog,
        "getOpenFileName",
        lambda *a, **k: (str(backup_zip), ""),
    )
    monkeypatch.setattr(
        backup_restore_page_module, "confirm_destructive_action", lambda *a, **k: False
    )

    def _fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("import_backup must not run when the user declines")

    monkeypatch.setattr(backup_restore_page_module, "import_backup", _fail_if_called)

    qtbot.mouseClick(page._import_button, backup_restore_page_module.Qt.MouseButton.LeftButton)


def test_import_button_rejects_invalid_zip_before_confirmation(
    qtbot, monkeypatch, page: BackupRestorePage, tmp_path
) -> None:
    garbage = tmp_path / "garbage.zip"
    garbage.write_bytes(b"not a zip")

    monkeypatch.setattr(
        backup_restore_page_module.QFileDialog,
        "getOpenFileName",
        lambda *a, **k: (str(garbage), ""),
    )

    def _fail_if_called(*args: object, **kwargs: object) -> bool:
        raise AssertionError("confirm_destructive_action must not run for an invalid backup")

    monkeypatch.setattr(backup_restore_page_module, "confirm_destructive_action", _fail_if_called)
    monkeypatch.setattr(backup_restore_page_module.QMessageBox, "critical", lambda *a, **k: None)

    qtbot.mouseClick(page._import_button, backup_restore_page_module.Qt.MouseButton.LeftButton)
