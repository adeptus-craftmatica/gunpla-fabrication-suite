"""Periodic, opt-in automatic backups — scheduling and retention around the
already-tested :func:`~gunpla_fabrication_suite.core.backup.export_backup`.

Runs via :class:`BackgroundJobManager` rather than synchronously, unlike the
manual export/import flow: an automatic backup only *reads* the live data
(no live-file-swap risk), so there's no reason to ever delay app startup,
especially for a large photo library. The worker thread does only pure file
I/O (:func:`_perform_backup`) — the settings write happens back on the main
thread, in a slot connected to ``BackgroundJobManager``'s signals, so
nothing ever mutates :class:`SettingsService` from a worker thread.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from gunpla_fabrication_suite.core.backup import export_backup
from gunpla_fabrication_suite.core.jobs import BackgroundJobManager
from gunpla_fabrication_suite.core.logging import get_logger
from gunpla_fabrication_suite.core.notifications import NotificationCenter, NotificationSeverity
from gunpla_fabrication_suite.core.paths import ApplicationPaths
from gunpla_fabrication_suite.core.settings import AutoBackupSettings, SettingsService

_logger = get_logger("auto_backup")

_BACKUP_PREFIX = "auto-backup-"


def is_backup_due(settings: AutoBackupSettings) -> bool:
    """Whether an automatic backup should run now, per ``settings``."""
    if not settings.enabled:
        return False
    if settings.last_backup_at is None:
        return True
    last_run = datetime.fromisoformat(settings.last_backup_at)
    return datetime.now(UTC) - last_run >= timedelta(days=settings.interval_days)


def _perform_backup(paths: ApplicationPaths, retention_count: int) -> Path:
    """Write one automatic backup and prune old ones. Runs on a worker thread."""
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination = paths.backups_dir / f"{_BACKUP_PREFIX}{timestamp}.zip"
    export_backup(paths, destination)
    _prune_old_backups(paths, retention_count)
    return destination


def _prune_old_backups(paths: ApplicationPaths, keep: int) -> None:
    """Delete all but the newest ``keep`` automatic backups.

    Only ever touches files with the ``auto-backup-`` prefix this module
    itself writes — manual exports and pre-import safety backups use their
    own distinct prefixes in the same directory and are never affected.
    """
    backups = sorted(paths.backups_dir.glob(f"{_BACKUP_PREFIX}*.zip"), reverse=True)
    for stale in backups[keep:]:
        stale.unlink(missing_ok=True)


def maybe_schedule_backup(
    paths: ApplicationPaths,
    settings_service: SettingsService,
    jobs: BackgroundJobManager,
    notifications: NotificationCenter,
) -> None:
    """Submit an automatic backup in the background, if one is due.

    Call once at startup. Does nothing (synchronously, immediately) if a
    backup isn't due yet.
    """
    settings = settings_service.current.auto_backup
    if not is_backup_due(settings):
        return

    retention_count = settings.retention_count
    handle = jobs.submit(
        "auto_backup", lambda _report_progress: _perform_backup(paths, retention_count)
    )

    def _on_succeeded(job_id: str, _result: object) -> None:
        if job_id != handle.id:
            return
        jobs.job_succeeded.disconnect(_on_succeeded)
        jobs.job_failed.disconnect(_on_failed)
        current = settings_service.current
        current.auto_backup.last_backup_at = datetime.now(UTC).isoformat()
        settings_service.save(current)
        _logger.info("auto_backup_completed")
        notifications.post(
            "Automatic backup completed.", severity=NotificationSeverity.INFO, source="auto_backup"
        )

    def _on_failed(job_id: str, error: str) -> None:
        if job_id != handle.id:
            return
        jobs.job_succeeded.disconnect(_on_succeeded)
        jobs.job_failed.disconnect(_on_failed)
        _logger.error("auto_backup_failed", error=error)
        notifications.post(
            f"Automatic backup failed: {error}",
            severity=NotificationSeverity.ERROR,
            source="auto_backup",
        )

    jobs.job_succeeded.connect(_on_succeeded)
    jobs.job_failed.connect(_on_failed)
