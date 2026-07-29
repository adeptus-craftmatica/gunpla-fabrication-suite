"""Tests for Kit Library business logic: creation, editing, archiving, and events."""

from __future__ import annotations

import pytest

from gunpla_fabrication_suite.core.events import EventBus
from gunpla_fabrication_suite.core.persistence import DatabaseService
from gunpla_fabrication_suite.plugins.kit_library.events import KitAdded, KitArchived, KitUpdated
from gunpla_fabrication_suite.plugins.kit_library.repositories.kit_repository import KitRepository
from gunpla_fabrication_suite.plugins.kit_library.schemas import KitCreate
from gunpla_fabrication_suite.plugins.kit_library.services.kit_service import (
    KitNotFoundError,
    KitService,
)


@pytest.fixture
def kit_service(database: DatabaseService, event_bus: EventBus) -> KitService:
    return KitService(KitRepository(database), event_bus)


def _create_payload(**overrides: object) -> KitCreate:
    defaults: dict[str, object] = {
        "manufacturer": "Bandai",
        "name": "RX-78-2 Gundam",
        "grade": "HG",
    }
    defaults.update(overrides)
    return KitCreate(**defaults)  # type: ignore[arg-type]


def test_create_kit_persists_and_returns_it(kit_service: KitService) -> None:
    created = kit_service.create_kit(_create_payload())

    assert created.name == "RX-78-2 Gundam"
    assert created.id

    listed = kit_service.list_kits()
    assert [kit.id for kit in listed] == [created.id]


def test_create_kit_publishes_kit_added_event(kit_service: KitService, event_bus: EventBus) -> None:
    events: list[KitAdded] = []
    event_bus.subscribe(KitAdded, events.append)

    created = kit_service.create_kit(_create_payload())

    assert len(events) == 1
    assert events[0].kit_id == created.id


def test_update_kit_changes_fields_and_publishes_event(
    kit_service: KitService, event_bus: EventBus
) -> None:
    events: list[KitUpdated] = []
    event_bus.subscribe(KitUpdated, events.append)
    created = kit_service.create_kit(_create_payload())

    updated = kit_service.update_kit(created.id, _create_payload(priority=3))

    assert updated.priority == 3
    assert updated.version == created.version + 1
    assert len(events) == 1


def test_update_kit_raises_for_unknown_id(kit_service: KitService) -> None:
    with pytest.raises(KitNotFoundError):
        kit_service.update_kit("missing-id", _create_payload())


def test_archive_kit_hides_it_from_default_listing(
    kit_service: KitService, event_bus: EventBus
) -> None:
    events: list[KitArchived] = []
    event_bus.subscribe(KitArchived, events.append)
    created = kit_service.create_kit(_create_payload())

    kit_service.archive_kit(created.id)

    assert kit_service.list_kits() == []
    assert kit_service.list_kits(include_archived=True)[0].is_deleted is True
    assert len(events) == 1


def test_restore_kit_makes_it_visible_again(kit_service: KitService) -> None:
    created = kit_service.create_kit(_create_payload())
    kit_service.archive_kit(created.id)

    restored = kit_service.restore_kit(created.id)

    assert restored.is_deleted is False
    assert [kit.id for kit in kit_service.list_kits()] == [created.id]


def test_archive_kit_raises_for_unknown_id(kit_service: KitService) -> None:
    with pytest.raises(KitNotFoundError):
        kit_service.archive_kit("missing-id")


def test_count_active_kits_reflects_archival(kit_service: KitService) -> None:
    first = kit_service.create_kit(_create_payload(name="First"))
    kit_service.create_kit(_create_payload(name="Second"))

    assert kit_service.count_active_kits() == 2

    kit_service.archive_kit(first.id)

    assert kit_service.count_active_kits() == 1
