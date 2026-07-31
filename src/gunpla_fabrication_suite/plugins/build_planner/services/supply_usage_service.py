"""Logic for logging (and undoing) a supply's use on a build.

Cost is only ever approximate: ``Supply`` stores the price paid for a whole
purchased batch, not a per-unit cost, and there's no field distinguishing
"quantity purchased" from the current, possibly-already-consumed
``quantity_on_hand``. Each usage snapshots ``purchase_price_cents /
quantity_on_hand`` at the moment it's logged so a later price/quantity
change doesn't retroactively change what a past build "cost."
"""

from __future__ import annotations

from gunpla_fabrication_suite.core.events import EventBus
from gunpla_fabrication_suite.plugins.build_planner.errors import SupplyUsageNotFoundError
from gunpla_fabrication_suite.plugins.build_planner.events import (
    SupplyUsageDeleted,
    SupplyUsageRecorded,
)
from gunpla_fabrication_suite.plugins.build_planner.models.supply_usage import SupplyUsage
from gunpla_fabrication_suite.plugins.build_planner.repositories.supply_usage_repository import (
    SupplyUsageRepository,
)
from gunpla_fabrication_suite.plugins.build_planner.schemas import (
    SupplyUsageCreate,
    SupplyUsageRead,
)
from gunpla_fabrication_suite.plugins.supplies.services.supply_service import SupplyService


class SupplyUsageService:
    """Logs supplies used on a build, keeping Supplies' stock in sync."""

    def __init__(
        self, repository: SupplyUsageRepository, supply_service: SupplyService, events: EventBus
    ) -> None:
        self._repository = repository
        self._supply_service = supply_service
        self._events = events

    def add_usage(self, build_id: str, data: SupplyUsageCreate) -> SupplyUsageRead:
        """Log a supply's use on a build, snapshotting its cost and decrementing its stock.

        Raises:
            gunpla_fabrication_suite.plugins.supplies.services.supply_service.SupplyNotFoundError:
                If ``data.supply_id`` does not exist.
        """
        supply = self._supply_service.get_supply(data.supply_id)  # raises SupplyNotFoundError

        unit_cost_cents = None
        estimated_cost_cents = None
        if supply.purchase_price_cents is not None and supply.quantity_on_hand > 0:
            unit_cost_cents = round(supply.purchase_price_cents / supply.quantity_on_hand)
            estimated_cost_cents = round(unit_cost_cents * data.quantity_used)

        usage = SupplyUsage(
            build_project_id=build_id,
            supply_id=data.supply_id,
            quantity_used=data.quantity_used,
            unit_snapshot=supply.unit,
            unit_cost_cents_snapshot=unit_cost_cents,
            estimated_cost_cents=estimated_cost_cents,
            notes=data.notes,
        )
        saved = self._repository.add(usage)
        self._supply_service.adjust_quantity(data.supply_id, -data.quantity_used)
        self._events.publish(
            SupplyUsageRecorded(
                usage_id=saved.id,
                build_id=build_id,
                supply_id=data.supply_id,
                quantity_used=data.quantity_used,
                created_at=saved.created_at,
            )
        )
        return SupplyUsageRead.model_validate(saved)

    def delete_usage(self, usage_id: str) -> None:
        """Delete a logged usage and restore its quantity to Supplies' stock.

        Raises:
            SupplyUsageNotFoundError: If ``usage_id`` does not exist.
        """
        usage = self._repository.get(usage_id)
        if usage is None:
            raise SupplyUsageNotFoundError(usage_id)
        # Restore stock before deleting the row: if adjust_quantity fails,
        # the usage record — and the fact that stock still needs
        # reconciling — isn't silently lost along with it.
        self._supply_service.adjust_quantity(usage.supply_id, usage.quantity_used)
        self._repository.delete(usage_id)
        self._events.publish(
            SupplyUsageDeleted(
                usage_id=usage_id,
                build_id=usage.build_project_id,
                supply_id=usage.supply_id,
                quantity_used=usage.quantity_used,
            )
        )

    def list_usages(self, build_id: str) -> list[SupplyUsageRead]:
        """List a build's logged supply usages, newest first."""
        usages = self._repository.list_for_project(build_id)
        return [SupplyUsageRead.model_validate(usage) for usage in usages]

    def total_cost_cents(self, build_id: str) -> int:
        """Sum of snapshotted costs across a build's usage rows (unknown-cost rows excluded)."""
        return sum(
            usage.estimated_cost_cents
            for usage in self._repository.list_for_project(build_id)
            if usage.estimated_cost_cents is not None
        )
