"""Business logic for managing supplies: the only entry point the UI should use."""

from __future__ import annotations

from datetime import UTC, datetime

from gunpla_fabrication_suite.core.events import EventBus
from gunpla_fabrication_suite.plugins.supplies.events import (
    SupplyAdded,
    SupplyArchived,
    SupplyUpdated,
)
from gunpla_fabrication_suite.plugins.supplies.models.supply import Supply
from gunpla_fabrication_suite.plugins.supplies.repositories.supply_repository import (
    SupplyRepository,
)
from gunpla_fabrication_suite.plugins.supplies.schemas import SupplyCreate, SupplyRead


class SupplyNotFoundError(LookupError):
    """Raised when an operation targets a supply id that does not exist."""

    def __init__(self, supply_id: str) -> None:
        super().__init__(f"No supply found with id {supply_id!r}")
        self.supply_id = supply_id


class SupplyService:
    """Validates, persists, and publishes events for supply changes."""

    def __init__(self, repository: SupplyRepository, events: EventBus) -> None:
        self._repository = repository
        self._events = events

    def create_supply(self, data: SupplyCreate) -> SupplyRead:
        """Add a new supply and publish :class:`SupplyAdded`."""
        supply = Supply(
            category=data.category.value,
            brand=data.brand,
            name=data.name,
            color_name=data.color_name,
            color_hex=data.color_hex,
            quantity_on_hand=data.quantity_on_hand,
            unit=data.unit,
            low_stock_threshold=data.low_stock_threshold,
            purchase_date=data.purchase_date,
            purchase_price_cents=data.purchase_price_cents,
            notes=data.notes,
        )
        supply.tags = data.tags

        saved = self._repository.add(supply)
        self._events.publish(
            SupplyAdded(supply_id=saved.id, name=saved.name, created_at=saved.created_at)
        )
        return SupplyRead.model_validate(saved)

    def update_supply(self, supply_id: str, data: SupplyCreate) -> SupplyRead:
        """Apply edits to an existing supply and publish :class:`SupplyUpdated`.

        Raises:
            SupplyNotFoundError: If ``supply_id`` does not exist.
        """
        existing = self._repository.get(supply_id)
        if existing is None:
            raise SupplyNotFoundError(supply_id)

        existing.category = data.category.value
        existing.brand = data.brand
        existing.name = data.name
        existing.color_name = data.color_name
        existing.color_hex = data.color_hex
        existing.quantity_on_hand = data.quantity_on_hand
        existing.unit = data.unit
        existing.low_stock_threshold = data.low_stock_threshold
        existing.purchase_date = data.purchase_date
        existing.purchase_price_cents = data.purchase_price_cents
        existing.notes = data.notes
        existing.tags = data.tags
        existing.version += 1

        saved = self._repository.update(existing)
        self._events.publish(SupplyUpdated(supply_id=saved.id, updated_at=saved.updated_at))
        return SupplyRead.model_validate(saved)

    def archive_supply(self, supply_id: str) -> None:
        """Soft-delete a supply, publishing :class:`SupplyArchived`.

        Raises:
            SupplyNotFoundError: If ``supply_id`` does not exist.
        """
        existing = self._repository.get(supply_id)
        if existing is None:
            raise SupplyNotFoundError(supply_id)
        existing.deleted_at = datetime.now(UTC)
        self._repository.update(existing)
        self._events.publish(SupplyArchived(supply_id=supply_id))

    def restore_supply(self, supply_id: str) -> SupplyRead:
        """Clear a supply's soft-deletion.

        Raises:
            SupplyNotFoundError: If ``supply_id`` does not exist.
        """
        existing = self._repository.get(supply_id)
        if existing is None:
            raise SupplyNotFoundError(supply_id)
        existing.deleted_at = None
        saved = self._repository.update(existing)
        return SupplyRead.model_validate(saved)

    def get_supply(self, supply_id: str) -> SupplyRead:
        """Fetch a single supply.

        Raises:
            SupplyNotFoundError: If ``supply_id`` does not exist.
        """
        existing = self._repository.get(supply_id)
        if existing is None:
            raise SupplyNotFoundError(supply_id)
        return SupplyRead.model_validate(existing)

    def list_supplies(self, *, include_archived: bool = False) -> list[SupplyRead]:
        """List supplies, excluding archived ones by default."""
        supplies = self._repository.list_all(include_archived=include_archived)
        return [SupplyRead.model_validate(supply) for supply in supplies]

    def count_active_supplies(self) -> int:
        """The number of non-archived supplies, for dashboard widgets."""
        return self._repository.count_active()

    def count_low_stock_supplies(self) -> int:
        """The number of active supplies at or below their low-stock threshold."""
        return self._repository.count_low_stock()
