"""Tests for automatic backup scheduling, retention, and settings persistence."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from gunpla_fabrication_suite.core.auto_backup import (
    _perform_backup,
    _prune_old_backups,
    is_backup_due,
    maybe_schedule_backup,
)
from gunpla_fabrication_suite.core.backup import validate_backup_manifest
from gunpla_fabrication_suite.core.notifications import NotificationCenter, NotificationSeverity
from gunpla_fabrication_suite.core.settings import AutoBackupSettings


def test_is_backup_due_false_when_disabled() -> None:
    settings = AutoBackupSettings(enabled=False)
    assert is_backup_due(settings) is False


def test_is_backup_due_true_when_never_run() -> None:
    settings = AutoBackupSettings(enabled=True, last_backup_at=None)
    assert is_backup_due(settings) is True


def test_is_backup_due_false_when_run_recently() -> None:
    settings = AutoBackupSettings(
        enabled=True,
        interval_days=7,
        last_backup_at=datetime.now(UTC).isoformat(),
    )
    assert is_backup_due(settings) is False


def test_is_backup_due_true_when_past_the_interval() -> None:
    settings = AutoBackupSettings(
        enabled=True,
        interval_days=7,
        last_backup_at=(datetime.now(UTC) - timedelta(days=10)).isoformat(),
    )
    assert is_backup_due(settings) is True


def test_perform_backup_writes_a_valid_zip(app_paths, database) -> None:
    destination = _perform_backup(app_paths, retention_count=5)

    assert destination.name.startswith("auto-backup-")
    manifest = validate_backup_manifest(destination)
    assert manifest.schema_revision is not None


def test_prune_old_backups_keeps_only_the_newest_n(app_paths) -> None:
    for i in range(5):
        (app_paths.backups_dir / f"auto-backup-2026010{i}T000000Z.zip").write_bytes(b"x")
    other_files = [
        app_paths.backups_dir / "gunpla-backup-20260101T000000Z.zip",
        app_paths.backups_dir / "pre-import-safety-20260101T000000Z.zip",
    ]
    for f in other_files:
        f.write_bytes(b"x")

    _prune_old_backups(app_paths, keep=2)

    remaining_auto = sorted(app_paths.backups_dir.glob("auto-backup-*.zip"))
    assert len(remaining_auto) == 2
    assert [p.name for p in remaining_auto] == [
        "auto-backup-20260103T000000Z.zip",
        "auto-backup-20260104T000000Z.zip",
    ]
    for f in other_files:
        assert f.exists()


def test_maybe_schedule_backup_does_nothing_when_not_due(
    app_paths, database, settings_service, jobs
) -> None:
    notifications = NotificationCenter()

    maybe_schedule_backup(app_paths, settings_service, jobs, notifications)

    assert list(app_paths.backups_dir.glob("auto-backup-*.zip")) == []
    assert notifications.history() == ()


def test_maybe_schedule_backup_runs_and_updates_settings_when_due(
    qtbot, app_paths, database, settings_service, jobs
) -> None:
    notifications = NotificationCenter()
    settings = settings_service.current
    settings.auto_backup.enabled = True
    settings.auto_backup.last_backup_at = None
    settings_service.save(settings)

    maybe_schedule_backup(app_paths, settings_service, jobs, notifications)

    qtbot.waitUntil(lambda: len(notifications.history()) > 0, timeout=5000)

    assert settings_service.current.auto_backup.last_backup_at is not None
    assert notifications.history()[-1].severity == NotificationSeverity.INFO
    assert list(app_paths.backups_dir.glob("auto-backup-*.zip"))
