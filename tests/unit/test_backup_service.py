"""Tests for the backup/restore zip-building, validation, and import logic."""

from __future__ import annotations

import zipfile

import pytest

import gunpla_fabrication_suite
from gunpla_fabrication_suite.core.backup import (
    BACKUP_FORMAT_VERSION,
    BackupIntegrityError,
    InvalidBackupError,
    export_backup,
    import_backup,
    validate_backup_manifest,
)
from gunpla_fabrication_suite.core.backup.schemas import BackupManifest


def test_export_backup_writes_expected_manifest_and_layout(
    app_paths, database, settings_service, tmp_path
) -> None:
    settings_service.save()
    destination = tmp_path / "backup.zip"

    export_backup(app_paths, destination)

    with zipfile.ZipFile(destination) as archive:
        names = archive.namelist()
    assert "manifest.json" in names
    assert "database/gunpla_fabrication_suite.sqlite3" in names
    assert "settings.json" in names

    manifest = validate_backup_manifest(destination)
    assert manifest.format_version == BACKUP_FORMAT_VERSION
    assert manifest.app_version == gunpla_fabrication_suite.__version__
    assert manifest.schema_revision is not None


def test_export_omits_media_dirs_that_have_no_files(app_paths, database, tmp_path) -> None:
    destination = tmp_path / "backup.zip"

    export_backup(app_paths, destination)

    with zipfile.ZipFile(destination) as archive:
        names = archive.namelist()
    assert not any(name.startswith("media/") for name in names)


def test_validate_backup_manifest_rejects_non_zip_file(tmp_path) -> None:
    garbage = tmp_path / "not_a_zip.zip"
    garbage.write_bytes(b"this is definitely not a zip file")

    with pytest.raises(InvalidBackupError):
        validate_backup_manifest(garbage)


def test_validate_backup_manifest_rejects_zip_without_manifest(tmp_path) -> None:
    source = tmp_path / "no_manifest.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("unrelated.txt", "hello")

    with pytest.raises(InvalidBackupError):
        validate_backup_manifest(source)


def test_validate_backup_manifest_rejects_unsupported_format_version(tmp_path) -> None:
    source = tmp_path / "future_format.zip"
    manifest = BackupManifest(
        format_version=999,
        app_version="0.0.0",
        export_timestamp="2026-01-01T00:00:00+00:00",
        schema_revision=None,
    )
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("manifest.json", manifest.model_dump_json())

    with pytest.raises(InvalidBackupError):
        validate_backup_manifest(source)


def test_import_backup_rejects_corrupt_database_without_touching_live_data(
    app_paths, database, tmp_path
) -> None:
    good_backup = tmp_path / "good.zip"
    export_backup(app_paths, good_backup)

    # Re-write the zip with the same manifest but a garbage database entry.
    corrupt_backup = tmp_path / "corrupt.zip"
    with zipfile.ZipFile(good_backup) as source_zip:
        manifest_bytes = source_zip.read("manifest.json")
    with zipfile.ZipFile(corrupt_backup, "w") as archive:
        archive.writestr("manifest.json", manifest_bytes)
        archive.writestr("database/gunpla_fabrication_suite.sqlite3", b"not a real sqlite file")

    before = sorted(p.name for p in app_paths.database_dir.iterdir())

    with pytest.raises(BackupIntegrityError):
        import_backup(app_paths, database, corrupt_backup)

    after = sorted(p.name for p in app_paths.database_dir.iterdir())
    assert before == after
