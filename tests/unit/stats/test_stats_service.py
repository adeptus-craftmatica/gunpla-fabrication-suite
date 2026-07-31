"""Tests for the Stats & Insights rollup computation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from gunpla_fabrication_suite.plugins.build_planner.schemas import BuildProjectCreate
from gunpla_fabrication_suite.plugins.kit_library.schemas import KitCreate
from gunpla_fabrication_suite.plugins.stats.services.stats_service import StatsService
from gunpla_fabrication_suite.plugins.supplies.schemas import SupplyCreate


def _stats(kit_service, build_service, work_session_service, supply_service, photo_service):
    return StatsService(
        kit_service, build_service, work_session_service, supply_service, photo_service
    )


def test_snapshot_tallies_kits_builds_and_hours(
    kit_service, build_service, work_session_service, supply_service, photo_service, existing_kit
) -> None:
    kit_service.create_kit(
        KitCreate(manufacturer="Bandai", name="Zaku II", grade="RG", purchase_price_cents=3000)
    )
    build = build_service.create_build(
        BuildProjectCreate(
            kit_id=existing_kit.id, title="Test Build", template_key="straight_build"
        )
    )
    started = datetime(2026, 1, 1, tzinfo=UTC)
    work_session_service.log_manual_session(
        build.id, started_at=started, ended_at=started + timedelta(hours=2)
    )

    snapshot = _stats(
        kit_service, build_service, work_session_service, supply_service, photo_service
    ).compute_snapshot()

    assert snapshot.total_kits_owned == 2
    assert snapshot.kits_by_grade == {"HG": 1, "RG": 1}
    assert snapshot.builds_by_status == {"planning": 1}
    assert snapshot.total_hours_built == 2.0
    assert snapshot.total_photos == 0


def test_snapshot_sums_kit_and_supply_purchase_price_without_double_counting(
    kit_service, build_service, work_session_service, supply_service, photo_service, existing_kit
) -> None:
    kit_service.update_kit(
        existing_kit.id,
        KitCreate(
            manufacturer=existing_kit.manufacturer,
            name=existing_kit.name,
            grade=existing_kit.grade,
            purchase_price_cents=6000,
        ),
    )
    supply_service.create_supply(
        SupplyCreate(brand="Tamiya", name="Panel Liner", purchase_price_cents=800)
    )

    snapshot = _stats(
        kit_service, build_service, work_session_service, supply_service, photo_service
    ).compute_snapshot()

    # Just the raw purchase prices, summed once each — not inflated by any
    # separate per-build usage-cost total (see StatsService's docstring).
    assert snapshot.total_spent_cents == 6000 + 800


def test_snapshot_excludes_archived_kits_from_grade_breakdown_but_not_total_hours(
    kit_service, build_service, work_session_service, supply_service, photo_service, existing_kit
) -> None:
    build = build_service.create_build(
        BuildProjectCreate(
            kit_id=existing_kit.id, title="Test Build", template_key="straight_build"
        )
    )
    started = datetime(2026, 1, 1, tzinfo=UTC)
    work_session_service.log_manual_session(
        build.id, started_at=started, ended_at=started + timedelta(hours=1)
    )
    build_service.archive_build(build.id)
    kit_service.archive_kit(existing_kit.id)

    snapshot = _stats(
        kit_service, build_service, work_session_service, supply_service, photo_service
    ).compute_snapshot()

    assert snapshot.total_kits_owned == 0
    assert snapshot.kits_by_grade == {}
    assert snapshot.builds_by_status == {}
    assert snapshot.total_hours_built == 1.0
