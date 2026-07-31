"""Tests for Supplies business logic: creation, editing, archiving, and low-stock tracking."""

from __future__ import annotations

import pytest

from gunpla_fabrication_suite.core.events import EventBus
from gunpla_fabrication_suite.core.persistence import DatabaseService
from gunpla_fabrication_suite.plugins.supplies.events import (
    SupplyAdded,
    SupplyArchived,
    SupplyUpdated,
)
from gunpla_fabrication_suite.plugins.supplies.repositories.supply_repository import (
    SupplyRepository,
)
from gunpla_fabrication_suite.plugins.supplies.schemas import SupplyCreate
from gunpla_fabrication_suite.plugins.supplies.services.supply_service import (
    SupplyNotFoundError,
    SupplyService,
)


@pytest.fixture
def supply_service(database: DatabaseService, event_bus: EventBus) -> SupplyService:
    return SupplyService(SupplyRepository(database), event_bus)


def _create_payload(**overrides: object) -> SupplyCreate:
    defaults: dict[str, object] = {
        "brand": "Mr. Color",
        "name": "Gundam Gray",
    }
    defaults.update(overrides)
    return SupplyCreate(**defaults)  # type: ignore[arg-type]


def test_create_supply_persists_and_returns_it(supply_service: SupplyService) -> None:
    created = supply_service.create_supply(_create_payload())

    assert created.name == "Gundam Gray"
    assert created.id

    listed = supply_service.list_supplies()
    assert [supply.id for supply in listed] == [created.id]


def test_create_supply_publishes_supply_added_event(
    supply_service: SupplyService, event_bus: EventBus
) -> None:
    events: list[SupplyAdded] = []
    event_bus.subscribe(SupplyAdded, events.append)

    created = supply_service.create_supply(_create_payload())

    assert len(events) == 1
    assert events[0].supply_id == created.id


def test_update_supply_changes_fields_and_publishes_event(
    supply_service: SupplyService, event_bus: EventBus
) -> None:
    events: list[SupplyUpdated] = []
    event_bus.subscribe(SupplyUpdated, events.append)
    created = supply_service.create_supply(_create_payload())

    updated = supply_service.update_supply(created.id, _create_payload(quantity_on_hand=5))

    assert updated.quantity_on_hand == 5
    assert updated.version == created.version + 1
    assert len(events) == 1


def test_update_supply_raises_for_unknown_id(supply_service: SupplyService) -> None:
    with pytest.raises(SupplyNotFoundError):
        supply_service.update_supply("missing-id", _create_payload())


def test_archive_supply_hides_it_from_default_listing(
    supply_service: SupplyService, event_bus: EventBus
) -> None:
    events: list[SupplyArchived] = []
    event_bus.subscribe(SupplyArchived, events.append)
    created = supply_service.create_supply(_create_payload())

    supply_service.archive_supply(created.id)

    assert supply_service.list_supplies() == []
    assert supply_service.list_supplies(include_archived=True)[0].is_deleted is True
    assert len(events) == 1


def test_restore_supply_makes_it_visible_again(supply_service: SupplyService) -> None:
    created = supply_service.create_supply(_create_payload())
    supply_service.archive_supply(created.id)

    restored = supply_service.restore_supply(created.id)

    assert restored.is_deleted is False
    assert [supply.id for supply in supply_service.list_supplies()] == [created.id]


def test_archive_supply_raises_for_unknown_id(supply_service: SupplyService) -> None:
    with pytest.raises(SupplyNotFoundError):
        supply_service.archive_supply("missing-id")


def test_count_active_supplies_reflects_archival(supply_service: SupplyService) -> None:
    first = supply_service.create_supply(_create_payload(name="First"))
    supply_service.create_supply(_create_payload(name="Second"))

    assert supply_service.count_active_supplies() == 2

    supply_service.archive_supply(first.id)

    assert supply_service.count_active_supplies() == 1


def test_supply_with_no_threshold_is_never_low_stock(supply_service: SupplyService) -> None:
    created = supply_service.create_supply(_create_payload(quantity_on_hand=0))

    assert created.is_low_stock is False
    assert supply_service.count_low_stock_supplies() == 0


def test_supply_at_or_below_threshold_is_low_stock(supply_service: SupplyService) -> None:
    low = supply_service.create_supply(
        _create_payload(name="Low", quantity_on_hand=1, low_stock_threshold=3)
    )
    supply_service.create_supply(
        _create_payload(name="Plenty", quantity_on_hand=10, low_stock_threshold=3)
    )

    assert low.is_low_stock is True
    assert supply_service.count_low_stock_supplies() == 1


def test_replenishing_a_supply_clears_low_stock_status(supply_service: SupplyService) -> None:
    created = supply_service.create_supply(
        _create_payload(quantity_on_hand=1, low_stock_threshold=3)
    )
    assert supply_service.count_low_stock_supplies() == 1

    updated = supply_service.update_supply(
        created.id, _create_payload(quantity_on_hand=10, low_stock_threshold=3)
    )

    assert updated.is_low_stock is False
    assert supply_service.count_low_stock_supplies() == 0


def test_archiving_a_low_stock_supply_removes_it_from_the_count(
    supply_service: SupplyService,
) -> None:
    created = supply_service.create_supply(
        _create_payload(quantity_on_hand=1, low_stock_threshold=3)
    )
    assert supply_service.count_low_stock_supplies() == 1

    supply_service.archive_supply(created.id)

    assert supply_service.count_low_stock_supplies() == 0


def test_adjust_quantity_decrements_by_the_given_delta(supply_service: SupplyService) -> None:
    created = supply_service.create_supply(_create_payload(quantity_on_hand=10))

    updated = supply_service.adjust_quantity(created.id, -3)

    assert updated.quantity_on_hand == 7


def test_adjust_quantity_round_trip_restores_the_original_value(
    supply_service: SupplyService,
) -> None:
    created = supply_service.create_supply(_create_payload(quantity_on_hand=10))

    supply_service.adjust_quantity(created.id, -4)
    restored = supply_service.adjust_quantity(created.id, 4)

    assert restored.quantity_on_hand == 10


def test_adjust_quantity_allows_a_negative_result(supply_service: SupplyService) -> None:
    created = supply_service.create_supply(_create_payload(quantity_on_hand=2))

    updated = supply_service.adjust_quantity(created.id, -5)

    assert updated.quantity_on_hand == -3


def test_adjust_quantity_publishes_supply_updated(
    supply_service: SupplyService, event_bus: EventBus
) -> None:
    events: list[SupplyUpdated] = []
    event_bus.subscribe(SupplyUpdated, events.append)
    created = supply_service.create_supply(_create_payload())

    supply_service.adjust_quantity(created.id, -1)

    assert len(events) == 1
    assert events[0].supply_id == created.id


def test_adjust_quantity_raises_for_unknown_id(supply_service: SupplyService) -> None:
    with pytest.raises(SupplyNotFoundError):
        supply_service.adjust_quantity("missing-id", -1)
