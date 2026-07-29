"""Tests for the Kit repository against a real, migrated SQLite database."""

from __future__ import annotations

from datetime import UTC, datetime

from gunpla_fabrication_suite.core.persistence import DatabaseService
from gunpla_fabrication_suite.plugins.kit_library.models.kit import CollectionStatus, Kit
from gunpla_fabrication_suite.plugins.kit_library.repositories.kit_repository import KitRepository


def _make_kit(**overrides: object) -> Kit:
    defaults: dict[str, object] = {
        "manufacturer": "Bandai",
        "name": "RX-78-2 Gundam",
        "grade": "HG",
        "status": CollectionStatus.WISHLIST.value,
    }
    defaults.update(overrides)
    return Kit(**defaults)  # type: ignore[arg-type]


def test_add_assigns_id_and_timestamps(database: DatabaseService) -> None:
    repository = KitRepository(database)

    saved = repository.add(_make_kit())

    assert saved.id
    assert saved.created_at is not None
    assert saved.version == 1


def test_get_returns_none_for_unknown_id(database: DatabaseService) -> None:
    repository = KitRepository(database)

    assert repository.get("does-not-exist") is None


def test_get_returns_previously_added_kit(database: DatabaseService) -> None:
    repository = KitRepository(database)
    saved = repository.add(_make_kit(name="Zaku II"))

    fetched = repository.get(saved.id)

    assert fetched is not None
    assert fetched.name == "Zaku II"


def test_list_all_excludes_archived_by_default(database: DatabaseService) -> None:
    repository = KitRepository(database)
    active = repository.add(_make_kit(name="Active Kit"))
    archived = repository.add(_make_kit(name="Archived Kit"))
    archived.deleted_at = datetime.now(UTC)
    repository.update(archived)

    visible = repository.list_all()

    assert [kit.id for kit in visible] == [active.id]


def test_list_all_includes_archived_when_requested(database: DatabaseService) -> None:
    repository = KitRepository(database)
    repository.add(_make_kit(name="Active Kit"))
    archived = repository.add(_make_kit(name="Archived Kit"))
    archived.deleted_at = datetime.now(UTC)
    repository.update(archived)

    visible = repository.list_all(include_archived=True)

    assert len(visible) == 2


def test_update_persists_field_changes(database: DatabaseService) -> None:
    repository = KitRepository(database)
    saved = repository.add(_make_kit(priority=0))

    saved.priority = 5
    repository.update(saved)

    assert repository.get(saved.id).priority == 5


def test_count_active_ignores_archived_kits(database: DatabaseService) -> None:
    repository = KitRepository(database)
    repository.add(_make_kit(name="One"))
    archived = repository.add(_make_kit(name="Two"))
    archived.deleted_at = datetime.now(UTC)
    repository.update(archived)

    assert repository.count_active() == 1


def test_tags_round_trip_through_the_csv_column(database: DatabaseService) -> None:
    repository = KitRepository(database)
    kit = _make_kit()
    kit.tags = ["gunpla", "hg", "priority"]

    saved = repository.add(kit)
    fetched = repository.get(saved.id)

    assert fetched.tags == ["gunpla", "hg", "priority"]
