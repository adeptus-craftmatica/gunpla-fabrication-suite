"""Tests for the Photo repository against a real, migrated SQLite database."""

from __future__ import annotations

from gunpla_fabrication_suite.core.persistence import DatabaseService
from gunpla_fabrication_suite.plugins.photography.models.photo import Photo
from gunpla_fabrication_suite.plugins.photography.models.photo_relationship import (
    PhotoRelationship,
)
from gunpla_fabrication_suite.plugins.photography.repositories.photo_repository import (
    PhotoRepository,
)


def _make_photo(**overrides: object) -> Photo:
    defaults: dict[str, object] = {
        "sha256_hash": "a" * 64,
        "original_filename": "wip.jpg",
        "source_path": "/tmp/wip.jpg",
        "original_relpath": "aa/wip.jpg",
        "thumbnail_relpath": "aa/wip_thumb.jpg",
        "preview_relpath": "aa/wip_preview.jpg",
        "width": 800,
        "height": 600,
        "file_size_bytes": 12345,
    }
    defaults.update(overrides)
    return Photo(**defaults)  # type: ignore[arg-type]


def test_add_photo_assigns_id_and_timestamps(database: DatabaseService) -> None:
    repository = PhotoRepository(database)

    saved = repository.add_photo(_make_photo())

    assert saved.id
    assert saved.created_at is not None
    assert saved.rating == 0
    assert saved.rotation_degrees == 0


def test_find_by_hash_returns_none_when_unknown(database: DatabaseService) -> None:
    repository = PhotoRepository(database)

    assert repository.find_by_hash("does-not-exist") is None


def test_find_by_hash_returns_the_matching_photo(database: DatabaseService) -> None:
    repository = PhotoRepository(database)
    saved = repository.add_photo(_make_photo(sha256_hash="b" * 64))

    found = repository.find_by_hash("b" * 64)

    assert found is not None
    assert found.id == saved.id


def test_list_all_photos_orders_newest_first(database: DatabaseService) -> None:
    repository = PhotoRepository(database)
    first = repository.add_photo(_make_photo(sha256_hash="c" * 64))
    second = repository.add_photo(_make_photo(sha256_hash="d" * 64))

    photos = repository.list_all_photos()

    assert [p.id for p in photos] == [second.id, first.id]


def test_delete_photo_cascades_to_its_relationships(database: DatabaseService) -> None:
    repository = PhotoRepository(database)
    photo = repository.add_photo(_make_photo(sha256_hash="e" * 64))
    repository.add_relationship(
        PhotoRelationship(photo_id=photo.id, entity_type="build_planner.build", entity_id="b-1")
    )

    repository.delete_photo(photo.id)

    assert repository.get_photo(photo.id) is None
    assert repository.list_relationships_for_photo(photo.id) == []


def test_list_relationships_for_entity_orders_by_order_index(database: DatabaseService) -> None:
    repository = PhotoRepository(database)
    photo_one = repository.add_photo(_make_photo(sha256_hash="f" * 64))
    photo_two = repository.add_photo(_make_photo(sha256_hash="1" * 64))

    added_second = repository.add_relationship(
        PhotoRelationship(
            photo_id=photo_two.id, entity_type="build_planner.build", entity_id="b-1", order_index=1
        )
    )
    added_first = repository.add_relationship(
        PhotoRelationship(
            photo_id=photo_one.id, entity_type="build_planner.build", entity_id="b-1", order_index=0
        )
    )

    ordered = repository.list_relationships_for_entity("build_planner.build", "b-1")

    assert [r.id for r in ordered] == [added_first.id, added_second.id]
