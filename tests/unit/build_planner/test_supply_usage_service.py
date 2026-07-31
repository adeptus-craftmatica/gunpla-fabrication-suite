"""Tests for logging supplies used on a build: cost snapshots and stock sync."""

from __future__ import annotations

import pytest

from gunpla_fabrication_suite.plugins.build_planner.errors import SupplyUsageNotFoundError
from gunpla_fabrication_suite.plugins.build_planner.events import (
    SupplyUsageDeleted,
    SupplyUsageRecorded,
)
from gunpla_fabrication_suite.plugins.build_planner.schemas import (
    BuildProjectCreate,
    SupplyUsageCreate,
)
from gunpla_fabrication_suite.plugins.build_planner.services.build_service import BuildService
from gunpla_fabrication_suite.plugins.build_planner.services.supply_usage_service import (
    SupplyUsageService,
)
from gunpla_fabrication_suite.plugins.kit_library.schemas import KitRead
from gunpla_fabrication_suite.plugins.supplies.schemas import SupplyCreate, SupplyRead
from gunpla_fabrication_suite.plugins.supplies.services.supply_service import (
    SupplyNotFoundError,
    SupplyService,
)


def _create_build(build_service: BuildService, existing_kit: KitRead) -> str:
    build = build_service.create_build(
        BuildProjectCreate(
            kit_id=existing_kit.id, title="Supplies Test", template_key="straight_build"
        )
    )
    return build.id


def test_add_usage_persists_and_appears_in_list(
    supply_usage_service: SupplyUsageService,
    build_service: BuildService,
    existing_kit: KitRead,
    existing_supply: SupplyRead,
) -> None:
    build_id = _create_build(build_service, existing_kit)

    supply_usage_service.add_usage(
        build_id, SupplyUsageCreate(supply_id=existing_supply.id, quantity_used=2)
    )

    usages = supply_usage_service.list_usages(build_id)
    assert len(usages) == 1
    assert usages[0].quantity_used == 2
    assert usages[0].unit_snapshot == existing_supply.unit


def test_add_usage_decrements_the_supply_stock(
    supply_usage_service: SupplyUsageService,
    supply_service: SupplyService,
    build_service: BuildService,
    existing_kit: KitRead,
    existing_supply: SupplyRead,
) -> None:
    build_id = _create_build(build_service, existing_kit)

    supply_usage_service.add_usage(
        build_id, SupplyUsageCreate(supply_id=existing_supply.id, quantity_used=3)
    )

    assert supply_service.get_supply(existing_supply.id).quantity_on_hand == 7


def test_add_usage_snapshots_cost_from_current_price_and_quantity(
    supply_usage_service: SupplyUsageService,
    build_service: BuildService,
    existing_kit: KitRead,
    existing_supply: SupplyRead,
) -> None:
    # existing_supply: purchase_price_cents=500, quantity_on_hand=10 -> 50 cents/unit
    build_id = _create_build(build_service, existing_kit)

    usage = supply_usage_service.add_usage(
        build_id, SupplyUsageCreate(supply_id=existing_supply.id, quantity_used=2)
    )

    assert usage.unit_cost_cents_snapshot == 50
    assert usage.estimated_cost_cents == 100


def test_add_usage_leaves_cost_unset_when_supply_has_no_price(
    supply_usage_service: SupplyUsageService,
    supply_service: SupplyService,
    build_service: BuildService,
    existing_kit: KitRead,
) -> None:
    unpriced = supply_service.create_supply(
        SupplyCreate(brand="Tamiya", name="Extra Thin Cement", quantity_on_hand=5)
    )
    build_id = _create_build(build_service, existing_kit)

    usage = supply_usage_service.add_usage(
        build_id, SupplyUsageCreate(supply_id=unpriced.id, quantity_used=1)
    )

    assert usage.unit_cost_cents_snapshot is None
    assert usage.estimated_cost_cents is None


def test_add_usage_raises_for_an_unknown_supply(
    supply_usage_service: SupplyUsageService, build_service: BuildService, existing_kit: KitRead
) -> None:
    build_id = _create_build(build_service, existing_kit)

    with pytest.raises(SupplyNotFoundError):
        supply_usage_service.add_usage(
            build_id, SupplyUsageCreate(supply_id="missing-id", quantity_used=1)
        )


def test_add_usage_publishes_supply_usage_recorded(
    supply_usage_service: SupplyUsageService,
    build_service: BuildService,
    existing_kit: KitRead,
    existing_supply: SupplyRead,
    event_bus,
) -> None:
    events: list[SupplyUsageRecorded] = []
    event_bus.subscribe(SupplyUsageRecorded, events.append)
    build_id = _create_build(build_service, existing_kit)

    usage = supply_usage_service.add_usage(
        build_id, SupplyUsageCreate(supply_id=existing_supply.id, quantity_used=2)
    )

    assert len(events) == 1
    assert events[0].usage_id == usage.id
    assert events[0].build_id == build_id
    assert events[0].supply_id == existing_supply.id
    assert events[0].quantity_used == 2


def test_delete_usage_removes_the_row_and_restores_stock(
    supply_usage_service: SupplyUsageService,
    supply_service: SupplyService,
    build_service: BuildService,
    existing_kit: KitRead,
    existing_supply: SupplyRead,
) -> None:
    build_id = _create_build(build_service, existing_kit)
    usage = supply_usage_service.add_usage(
        build_id, SupplyUsageCreate(supply_id=existing_supply.id, quantity_used=4)
    )
    assert supply_service.get_supply(existing_supply.id).quantity_on_hand == 6

    supply_usage_service.delete_usage(usage.id)

    assert supply_usage_service.list_usages(build_id) == []
    assert supply_service.get_supply(existing_supply.id).quantity_on_hand == 10


def test_delete_usage_publishes_supply_usage_deleted(
    supply_usage_service: SupplyUsageService,
    build_service: BuildService,
    existing_kit: KitRead,
    existing_supply: SupplyRead,
    event_bus,
) -> None:
    events: list[SupplyUsageDeleted] = []
    event_bus.subscribe(SupplyUsageDeleted, events.append)
    build_id = _create_build(build_service, existing_kit)
    usage = supply_usage_service.add_usage(
        build_id, SupplyUsageCreate(supply_id=existing_supply.id, quantity_used=1)
    )

    supply_usage_service.delete_usage(usage.id)

    assert len(events) == 1
    assert events[0].usage_id == usage.id
    assert events[0].supply_id == existing_supply.id
    assert events[0].quantity_used == 1


def test_delete_usage_raises_for_an_unknown_id(supply_usage_service: SupplyUsageService) -> None:
    with pytest.raises(SupplyUsageNotFoundError):
        supply_usage_service.delete_usage("missing-id")


def test_total_cost_cents_sums_across_usage_rows(
    supply_usage_service: SupplyUsageService,
    supply_service: SupplyService,
    build_service: BuildService,
    existing_kit: KitRead,
    existing_supply: SupplyRead,
) -> None:
    # A second, independent supply keeps each row's cost simple to reason
    # about (100 + 500) — using the same supply twice would also correctly
    # sum, but the second row's snapshot would price off the *already
    # decremented* stock from the first, per add_usage's documented drift.
    other_supply = supply_service.create_supply(
        SupplyCreate(
            brand="Tamiya", name="Panel Liner", quantity_on_hand=4, purchase_price_cents=2000
        )
    )
    build_id = _create_build(build_service, existing_kit)
    supply_usage_service.add_usage(
        build_id, SupplyUsageCreate(supply_id=existing_supply.id, quantity_used=2)
    )
    supply_usage_service.add_usage(
        build_id, SupplyUsageCreate(supply_id=other_supply.id, quantity_used=1)
    )

    assert supply_usage_service.total_cost_cents(build_id) == 600
