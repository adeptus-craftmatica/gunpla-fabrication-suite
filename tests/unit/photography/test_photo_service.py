"""Tests for the Photography service: import, dedup, attach/detach, hero, delete."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from gunpla_fabrication_suite.plugins.photography.errors import (
    PhotoNotFoundError,
    RelationshipNotFoundError,
)
from gunpla_fabrication_suite.plugins.photography.events import (
    PhotoAttached,
    PhotoDeleted,
    PhotoDetached,
    PhotoImported,
)
from gunpla_fabrication_suite.plugins.photography.services.photo_service import PhotoService

_ENTITY_TYPE = "build_planner.build"


def _make_jpeg(path: Path, *, color: tuple[int, int, int] = (200, 40, 40), size=(640, 480)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color=color).save(path, "JPEG")
    return path


def test_import_photo_creates_managed_files(photo_service: PhotoService, tmp_path: Path) -> None:
    source = _make_jpeg(tmp_path / "incoming" / "wip.jpg")

    photo = photo_service.import_photo(source)

    assert photo.width == 640
    assert photo.height == 480
    assert photo.original_filename == "wip.jpg"
    assert photo_service.resolve_thumbnail_path(photo).exists()
    assert photo_service.resolve_preview_path(photo).exists()


def test_importing_identical_bytes_reuses_the_same_photo(
    photo_service: PhotoService, tmp_path: Path
) -> None:
    original = _make_jpeg(tmp_path / "incoming" / "original.jpg")
    duplicate = tmp_path / "incoming" / "copy.jpg"
    duplicate.write_bytes(original.read_bytes())

    first = photo_service.import_photo(original)
    second = photo_service.import_photo(duplicate)

    assert first.id == second.id
    assert len(photo_service.list_all_photos()) == 1


def test_attach_links_a_photo_to_an_entity(photo_service: PhotoService, tmp_path: Path) -> None:
    photo = photo_service.import_photo(_make_jpeg(tmp_path / "wip.jpg"))

    attached = photo_service.attach(photo.id, _ENTITY_TYPE, "build-1")

    assert attached.entity_id == "build-1"
    assert attached.is_hero is False
    assert photo_service.list_photos_for_entity(_ENTITY_TYPE, "build-1") == [attached]


def test_reattaching_the_same_entity_is_idempotent(
    photo_service: PhotoService, tmp_path: Path
) -> None:
    photo = photo_service.import_photo(_make_jpeg(tmp_path / "wip.jpg"))

    first = photo_service.attach(photo.id, _ENTITY_TYPE, "build-1")
    second = photo_service.attach(photo.id, _ENTITY_TYPE, "build-1")

    assert first.relationship_id == second.relationship_id
    assert len(photo_service.list_photos_for_entity(_ENTITY_TYPE, "build-1")) == 1


def test_a_photo_can_be_shared_across_two_entities(
    photo_service: PhotoService, tmp_path: Path
) -> None:
    photo = photo_service.import_photo(_make_jpeg(tmp_path / "wip.jpg"))

    photo_service.attach(photo.id, _ENTITY_TYPE, "build-1")
    photo_service.attach(photo.id, _ENTITY_TYPE, "build-2")

    assert photo_service.count_relationships(photo.id) == 2


def test_detach_removes_the_relationship_but_keeps_the_photo(
    photo_service: PhotoService, tmp_path: Path
) -> None:
    photo = photo_service.import_photo(_make_jpeg(tmp_path / "wip.jpg"))
    attached = photo_service.attach(photo.id, _ENTITY_TYPE, "build-1")

    photo_service.detach(attached.relationship_id)

    assert photo_service.list_photos_for_entity(_ENTITY_TYPE, "build-1") == []
    assert photo_service.get_photo(photo.id) == photo


def test_detach_raises_for_an_unknown_relationship(photo_service: PhotoService) -> None:
    with pytest.raises(RelationshipNotFoundError):
        photo_service.detach("does-not-exist")


def test_set_hero_clears_any_previous_hero_for_the_same_entity(
    photo_service: PhotoService, tmp_path: Path
) -> None:
    first = photo_service.attach(
        photo_service.import_photo(_make_jpeg(tmp_path / "one.jpg", color=(10, 10, 10))).id,
        _ENTITY_TYPE,
        "build-1",
    )
    second = photo_service.attach(
        photo_service.import_photo(_make_jpeg(tmp_path / "two.jpg", color=(220, 220, 220))).id,
        _ENTITY_TYPE,
        "build-1",
    )

    photo_service.set_hero(first.relationship_id)
    photo_service.set_hero(second.relationship_id)

    entity_photos = {p.relationship_id: p.is_hero for p in photo_service.list_photos_for_entity(
        _ENTITY_TYPE, "build-1"
    )}
    assert entity_photos[first.relationship_id] is False
    assert entity_photos[second.relationship_id] is True


def test_update_details_persists_caption_rating_and_rotation(
    photo_service: PhotoService, tmp_path: Path
) -> None:
    photo = photo_service.import_photo(_make_jpeg(tmp_path / "wip.jpg"))

    updated = photo_service.update_details(
        photo.id, caption="Primer coat done", rating=4, rotation_degrees=450
    )

    assert updated.caption == "Primer coat done"
    assert updated.rating == 4
    assert updated.rotation_degrees == 90  # 450 % 360


def test_update_details_clamps_rating_to_valid_range(
    photo_service: PhotoService, tmp_path: Path
) -> None:
    photo = photo_service.import_photo(_make_jpeg(tmp_path / "wip.jpg"))

    updated = photo_service.update_details(photo.id, caption=None, rating=99, rotation_degrees=0)

    assert updated.rating == 5


def test_delete_photo_removes_the_database_row_and_the_files_on_disk(
    photo_service: PhotoService, tmp_path: Path
) -> None:
    photo = photo_service.import_photo(_make_jpeg(tmp_path / "wip.jpg"))
    thumbnail_path = photo_service.resolve_thumbnail_path(photo)
    preview_path = photo_service.resolve_preview_path(photo)
    assert thumbnail_path.exists() and preview_path.exists()

    photo_service.delete_photo(photo.id)

    assert not thumbnail_path.exists()
    assert not preview_path.exists()
    with pytest.raises(PhotoNotFoundError):
        photo_service.get_photo(photo.id)


def test_delete_photo_also_removes_every_relationship(
    photo_service: PhotoService, tmp_path: Path
) -> None:
    photo = photo_service.import_photo(_make_jpeg(tmp_path / "wip.jpg"))
    photo_service.attach(photo.id, _ENTITY_TYPE, "build-1")
    photo_service.attach(photo.id, _ENTITY_TYPE, "build-2")

    photo_service.delete_photo(photo.id)

    assert photo_service.list_photos_for_entity(_ENTITY_TYPE, "build-1") == []
    assert photo_service.list_photos_for_entity(_ENTITY_TYPE, "build-2") == []


def test_get_photo_raises_for_an_unknown_id(photo_service: PhotoService) -> None:
    with pytest.raises(PhotoNotFoundError):
        photo_service.get_photo("does-not-exist")


def test_import_and_attach_publish_events_but_idempotent_reattach_does_not(
    photo_service: PhotoService, tmp_path: Path, event_bus
) -> None:
    received: list[object] = []
    event_bus.subscribe(PhotoImported, received.append)
    event_bus.subscribe(PhotoAttached, received.append)
    event_bus.subscribe(PhotoDetached, received.append)
    event_bus.subscribe(PhotoDeleted, received.append)

    photo = photo_service.import_photo(_make_jpeg(tmp_path / "wip.jpg"))
    attached = photo_service.attach(photo.id, _ENTITY_TYPE, "build-1")
    photo_service.attach(photo.id, _ENTITY_TYPE, "build-1")  # idempotent, no new event
    photo_service.detach(attached.relationship_id)
    photo_service.delete_photo(photo.id)

    kinds = [type(event).__name__ for event in received]
    assert kinds == ["PhotoImported", "PhotoAttached", "PhotoDetached", "PhotoDeleted"]


def test_list_all_photos_orders_newest_first(photo_service: PhotoService, tmp_path: Path) -> None:
    first = photo_service.import_photo(_make_jpeg(tmp_path / "one.jpg", color=(10, 10, 10)))
    second = photo_service.import_photo(_make_jpeg(tmp_path / "two.jpg", color=(20, 20, 20)))

    photos = photo_service.list_all_photos()

    assert [p.id for p in photos] == [second.id, first.id]
