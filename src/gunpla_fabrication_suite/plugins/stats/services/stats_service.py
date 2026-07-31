"""Computes a rolled-up snapshot by tallying the other plugins' existing services.

At hobbyist collection scale (dozens, not thousands, of records) this loops
in Python rather than adding collection-wide SQL aggregates to four other
plugins' repositories — ``WorkSessionService.total_hours`` is already
per-build; this calls it once per build from ``BuildService.list_builds()``.

"Total spent" is the sum of what was actually paid for kits and supplies
(``purchase_price_cents``, archived items included — that money was still
spent). ``SupplyUsageService.total_cost_cents`` is deliberately *not* added
on top: it's an allocation of a supply's own purchase price across the
builds that consumed it, not additional money spent — summing both would
double-count the same purchase.
"""

from __future__ import annotations

from gunpla_fabrication_suite.plugins.build_planner.services.build_service import BuildService
from gunpla_fabrication_suite.plugins.build_planner.services.work_session_service import (
    WorkSessionService,
)
from gunpla_fabrication_suite.plugins.kit_library.services.kit_service import KitService
from gunpla_fabrication_suite.plugins.photography.services.photo_service import PhotoService
from gunpla_fabrication_suite.plugins.stats.schemas import StatsSnapshot
from gunpla_fabrication_suite.plugins.supplies.services.supply_service import SupplyService


class StatsService:
    """Rolls up numbers across Kit Library, Build Planner, Supplies, and Photography."""

    def __init__(
        self,
        kit_service: KitService,
        build_service: BuildService,
        work_session_service: WorkSessionService,
        supply_service: SupplyService,
        photo_service: PhotoService,
    ) -> None:
        self._kit_service = kit_service
        self._build_service = build_service
        self._work_session_service = work_session_service
        self._supply_service = supply_service
        self._photo_service = photo_service

    def compute_snapshot(self) -> StatsSnapshot:
        """Tally kits, builds, hours, and spend into one snapshot."""
        kits = self._kit_service.list_kits(include_archived=False)
        kits_by_grade: dict[str, int] = {}
        for kit in kits:
            kits_by_grade[kit.grade] = kits_by_grade.get(kit.grade, 0) + 1

        builds_by_status: dict[str, int] = {}
        for build in self._build_service.list_builds(include_archived=False):
            builds_by_status[build.status] = builds_by_status.get(build.status, 0) + 1

        # "across ALL builds" for hours: an archived build's hours were still
        # genuinely spent, unlike its kit/grade tally above.
        all_builds = self._build_service.list_builds(include_archived=True)
        total_hours = round(
            sum(self._work_session_service.total_hours(build.id) for build in all_builds), 2
        )

        all_kits = self._kit_service.list_kits(include_archived=True)
        kit_spend_cents = sum(
            kit.purchase_price_cents for kit in all_kits if kit.purchase_price_cents is not None
        )
        supplies = self._supply_service.list_supplies(include_archived=True)
        supply_spend_cents = sum(
            supply.purchase_price_cents
            for supply in supplies
            if supply.purchase_price_cents is not None
        )

        return StatsSnapshot(
            total_kits_owned=self._kit_service.count_active_kits(),
            kits_by_grade=kits_by_grade,
            builds_by_status=builds_by_status,
            total_hours_built=total_hours,
            total_spent_cents=kit_spend_cents + supply_spend_cents,
            total_photos=len(self._photo_service.list_all_photos()),
        )
