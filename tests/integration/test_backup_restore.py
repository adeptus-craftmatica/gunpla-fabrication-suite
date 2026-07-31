"""Integration tests for a full backup export/import round trip against real
SQLite files and media, using two fully independent ApplicationPaths."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from gunpla_fabrication_suite.core.backup import export_backup, import_backup
from gunpla_fabrication_suite.core.events import EventBus
from gunpla_fabrication_suite.core.paths import ApplicationPaths
from gunpla_fabrication_suite.core.persistence import DatabaseService
from gunpla_fabrication_suite.plugins.kit_library.repositories.kit_repository import KitRepository
from gunpla_fabrication_suite.plugins.kit_library.schemas import KitCreate
from gunpla_fabrication_suite.plugins.kit_library.services.kit_service import KitService
from gunpla_fabrication_suite.plugins.photography.repositories import PhotoRepository
from gunpla_fabrication_suite.plugins.photography.services import PhotoService


def _make_jpeg(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (640, 480), color=(30, 90, 160)).save(path, "JPEG")
    return path


def test_round_trip_preserves_kit_and_photo_data(tmp_path: Path) -> None:
    paths_a = ApplicationPaths(root=tmp_path / "a")
    paths_a.ensure_exists()
    db_a = DatabaseService(paths_a.database_file)
    db_a.migrate()

    events_a = EventBus()
    kit_service_a = KitService(KitRepository(db_a), events_a)
    photo_service_a = PhotoService(PhotoRepository(db_a), paths_a, events_a)

    kit = kit_service_a.create_kit(
        KitCreate(manufacturer="Bandai", name="RX-78-2 Gundam", grade="HG")
    )
    photo = photo_service_a.import_photo(_make_jpeg(tmp_path / "incoming" / "wip.jpg"))
    original_bytes = (paths_a.media_originals_dir / photo.original_relpath).read_bytes()
    thumbnail_bytes = photo_service_a.resolve_thumbnail_path(photo).read_bytes()
    preview_bytes = photo_service_a.resolve_preview_path(photo).read_bytes()

    backup_zip = tmp_path / "backup.zip"
    export_backup(paths_a, backup_zip)

    paths_b = ApplicationPaths(root=tmp_path / "b")
    paths_b.ensure_exists()
    db_b = DatabaseService(paths_b.database_file)
    db_b.migrate()

    result = import_backup(paths_b, db_b, backup_zip)

    assert result.safety_backup_path.exists()
    assert result.restored_media_file_count == 3  # original + thumbnail + preview

    db_b2 = DatabaseService(paths_b.database_file)
    kits_b = KitRepository(db_b2).list_all()
    assert len(kits_b) == 1
    assert kits_b[0].name == kit.name
    assert kits_b[0].manufacturer == kit.manufacturer
    assert kits_b[0].grade == kit.grade

    photos_b = PhotoRepository(db_b2).list_all_photos()
    assert len(photos_b) == 1
    photo_b = photos_b[0]
    assert photo_b.sha256_hash == photo.sha256_hash
    assert (paths_b.media_originals_dir / photo_b.original_relpath).read_bytes() == original_bytes
    assert (
        paths_b.media_thumbnails_dir / photo_b.thumbnail_relpath
    ).read_bytes() == thumbnail_bytes
    assert (paths_b.media_previews_dir / photo_b.preview_relpath).read_bytes() == preview_bytes

    db_a.dispose()
    db_b2.dispose()


def test_import_leaves_bak_directories_for_manual_recovery(tmp_path: Path) -> None:
    paths_a = ApplicationPaths(root=tmp_path / "a")
    paths_a.ensure_exists()
    db_a = DatabaseService(paths_a.database_file)
    db_a.migrate()
    KitService(KitRepository(db_a), EventBus()).create_kit(
        KitCreate(manufacturer="Bandai", name="Zaku II", grade="RG")
    )
    backup_zip = tmp_path / "backup.zip"
    export_backup(paths_a, backup_zip)

    paths_b = ApplicationPaths(root=tmp_path / "b")
    paths_b.ensure_exists()
    db_b = DatabaseService(paths_b.database_file)
    db_b.migrate()

    import_backup(paths_b, db_b, backup_zip)

    backups = [p.name for p in paths_b.root.iterdir() if ".bak-" in p.name]
    assert any(name.startswith("database.bak-") for name in backups)

    db_a.dispose()
