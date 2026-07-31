"""Export the whole app's data (database, media, settings) to one portable
zip, and import it back — the only place in the app that reads or writes
:class:`~gunpla_fabrication_suite.core.paths.ApplicationPaths`' managed
directories directly rather than through a plugin's service.
"""

from __future__ import annotations

import shutil
import sqlite3
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from gunpla_fabrication_suite import __version__
from gunpla_fabrication_suite.core.backup.schemas import BACKUP_FORMAT_VERSION, BackupManifest
from gunpla_fabrication_suite.core.logging import get_logger
from gunpla_fabrication_suite.core.paths import ApplicationPaths
from gunpla_fabrication_suite.core.persistence import DatabaseService
from gunpla_fabrication_suite.core.persistence.migrations import run_migrations

_logger = get_logger("backup")

_MANIFEST_ARCNAME = "manifest.json"
_DATABASE_ARCNAME = "database/gunpla_fabrication_suite.sqlite3"
_SETTINGS_ARCNAME = "settings.json"
_MEDIA_SUBDIRS = ("originals", "previews", "thumbnails")


class InvalidBackupError(ValueError):
    """Raised when a backup file is unreadable, malformed, or unsupported."""


class BackupIntegrityError(RuntimeError):
    """Raised when a backup's database fails integrity check or migration."""


@dataclass(frozen=True, slots=True)
class ImportResult:
    """What happened during a successful :func:`import_backup`."""

    safety_backup_path: Path
    imported_schema_revision: str | None
    restored_media_file_count: int


def _timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _read_schema_revision(database_file: Path) -> str | None:
    """The Alembic revision recorded inside ``database_file``, or ``None``."""
    connection = sqlite3.connect(str(database_file))
    try:
        row = connection.execute("SELECT version_num FROM alembic_version LIMIT 1").fetchone()
        return row[0] if row else None
    except sqlite3.OperationalError:
        return None
    finally:
        connection.close()


def _snapshot_database(database_file: Path, destination: Path) -> None:
    """Write a consistent copy of ``database_file`` to ``destination``.

    Uses SQLite's own backup API via a fresh, independent connection —
    safe against a live database in WAL mode (readers don't block the
    writer or each other) without needing to touch the app's SQLAlchemy
    engine at all.
    """
    source = sqlite3.connect(str(database_file))
    try:
        target = sqlite3.connect(str(destination))
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()


def export_backup(paths: ApplicationPaths, destination: Path) -> Path:
    """Write a full backup zip (database + media + settings) to ``destination``."""
    tmp_destination = destination.with_suffix(destination.suffix + ".tmp")
    tmp_destination.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(tmp_destination, "w", zipfile.ZIP_DEFLATED) as archive:
        db_snapshot = tmp_destination.with_suffix(".db-snapshot")
        try:
            _snapshot_database(paths.database_file, db_snapshot)
            manifest = BackupManifest(
                format_version=BACKUP_FORMAT_VERSION,
                app_version=__version__,
                export_timestamp=datetime.now(UTC).isoformat(),
                schema_revision=_read_schema_revision(db_snapshot),
            )
            archive.writestr(_MANIFEST_ARCNAME, manifest.model_dump_json(indent=2))
            archive.write(db_snapshot, _DATABASE_ARCNAME)
        finally:
            db_snapshot.unlink(missing_ok=True)

        if paths.settings_file.exists():
            archive.write(paths.settings_file, _SETTINGS_ARCNAME)

        media_roots = {
            "originals": paths.media_originals_dir,
            "previews": paths.media_previews_dir,
            "thumbnails": paths.media_thumbnails_dir,
        }
        for subdir, root in media_roots.items():
            if not root.is_dir():
                continue
            for file_path in root.rglob("*"):
                if file_path.is_file():
                    arcname = f"media/{subdir}/{file_path.relative_to(root).as_posix()}"
                    archive.write(file_path, arcname)

    tmp_destination.replace(destination)
    _logger.info("backup_exported", destination=str(destination))
    return destination


def validate_backup_manifest(source: Path) -> BackupManifest:
    """Read and validate just ``manifest.json`` from ``source``.

    Raises:
        InvalidBackupError: If ``source`` isn't a readable zip, has no
            manifest, or declares an unsupported ``format_version``.
    """
    try:
        with zipfile.ZipFile(source) as archive:
            raw = archive.read(_MANIFEST_ARCNAME)
    except (zipfile.BadZipFile, KeyError, OSError) as exc:
        raise InvalidBackupError(f"{source} is not a valid backup file: {exc}") from exc

    try:
        manifest = BackupManifest.model_validate_json(raw)
    except Exception as exc:
        raise InvalidBackupError(f"{source}'s manifest is unreadable: {exc}") from exc

    if manifest.format_version != BACKUP_FORMAT_VERSION:
        raise InvalidBackupError(
            f"Unsupported backup format version {manifest.format_version} "
            f"(expected {BACKUP_FORMAT_VERSION})."
        )
    return manifest


def _reject_unsafe_zip_members(archive: zipfile.ZipFile, source: Path) -> None:
    for member in archive.namelist():
        if member.startswith("/") or ".." in Path(member).parts:
            raise InvalidBackupError(f"{source} contains an unsafe path: {member!r}")


def import_backup(
    paths: ApplicationPaths,
    database: DatabaseService,
    source: Path,
    *,
    migrations_root: Path | None = None,
) -> ImportResult:
    """Validate, stage, and swap in ``source``'s data, replacing everything live.

    Nothing about the current live database/media/settings is touched
    until the incoming backup has been fully extracted, integrity-checked,
    and migrated to the current schema — so a failure at any point before
    that leaves the live app exactly as it was.

    Raises:
        InvalidBackupError: If ``source`` isn't a valid, readable backup.
        BackupIntegrityError: If the backup's database fails an integrity
            check or can't be migrated to the current schema.
    """
    validate_backup_manifest(source)

    staging_root = paths.recovery_dir / "import-staging"
    shutil.rmtree(staging_root, ignore_errors=True)
    staging_root.mkdir(parents=True)

    try:
        with zipfile.ZipFile(source) as archive:
            _reject_unsafe_zip_members(archive, source)
            archive.extractall(staging_root)

        staged_db = staging_root / "database" / "gunpla_fabrication_suite.sqlite3"
        if not staged_db.is_file():
            raise InvalidBackupError(f"{source} has no database entry.")

        staged_service = DatabaseService(staged_db)
        try:
            try:
                integrity_ok = staged_service.check_integrity()
            except Exception as exc:
                raise BackupIntegrityError(f"{source}'s database could not be read: {exc}") from exc
            if not integrity_ok:
                raise BackupIntegrityError(f"{source}'s database failed an integrity check.")
            try:
                run_migrations(staged_db, migrations_root)
            except Exception as exc:
                raise BackupIntegrityError(
                    f"{source}'s database could not be migrated to the current schema: {exc}"
                ) from exc
        finally:
            staged_service.dispose()

        # Only now that the incoming data is proven valid: back up the
        # current live data before touching anything, so a doomed import
        # never produces a pointless safety backup.
        timestamp = _timestamp()
        safety_backup_path = paths.backups_dir / f"pre-import-safety-{timestamp}.zip"
        export_backup(paths, safety_backup_path)

        database.dispose()

        for live_dir in (paths.database_dir, paths.media_dir):
            if live_dir.exists():
                live_dir.rename(live_dir.with_name(f"{live_dir.name}.bak-{timestamp}"))
        if paths.settings_file.exists():
            paths.settings_file.rename(
                paths.settings_file.with_name(f"{paths.settings_file.name}.bak-{timestamp}")
            )

        paths.database_dir.mkdir(parents=True)
        staged_db.rename(paths.database_file)

        staged_media = staging_root / "media"
        restored_media_file_count = 0
        if staged_media.is_dir():
            staged_media.rename(paths.media_dir)
            restored_media_file_count = sum(1 for f in paths.media_dir.rglob("*") if f.is_file())
        # A backup may have omitted one or all media subdirs entirely (only
        # non-empty ones are written by export_backup) — ensure every
        # managed directory exists regardless of what the backup contained.
        paths.ensure_exists()

        staged_settings = staging_root / "settings.json"
        if staged_settings.is_file():
            staged_settings.rename(paths.settings_file)

        _logger.info("backup_imported", source=str(source), safety_backup=str(safety_backup_path))
        return ImportResult(
            safety_backup_path=safety_backup_path,
            imported_schema_revision=_read_schema_revision(paths.database_file),
            restored_media_file_count=restored_media_file_count,
        )
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)
