"""Business logic for managing kits: the only entry point the UI should use."""

from __future__ import annotations

from datetime import UTC, datetime

from gunpla_fabrication_suite.core.events import EventBus
from gunpla_fabrication_suite.plugins.kit_library.events import KitAdded, KitArchived, KitUpdated
from gunpla_fabrication_suite.plugins.kit_library.models.kit import Kit
from gunpla_fabrication_suite.plugins.kit_library.repositories.kit_repository import KitRepository
from gunpla_fabrication_suite.plugins.kit_library.schemas import KitCreate, KitRead


class KitNotFoundError(LookupError):
    """Raised when an operation targets a kit id that does not exist."""

    def __init__(self, kit_id: str) -> None:
        super().__init__(f"No kit found with id {kit_id!r}")
        self.kit_id = kit_id


class KitService:
    """Validates, persists, and publishes events for kit changes."""

    def __init__(self, repository: KitRepository, events: EventBus) -> None:
        self._repository = repository
        self._events = events

    def create_kit(self, data: KitCreate) -> KitRead:
        """Add a new kit and publish :class:`KitAdded`."""
        kit = Kit(
            manufacturer=data.manufacturer,
            name=data.name,
            grade=data.grade,
            scale=data.scale,
            mobile_suit_designation=data.mobile_suit_designation,
            product_number=data.product_number,
            series=data.series,
            release_year=data.release_year,
            status=data.status.value,
            priority=data.priority,
            difficulty_estimate=data.difficulty_estimate,
            estimated_build_hours=data.estimated_build_hours,
            purchase_date=data.purchase_date,
            purchase_price_cents=data.purchase_price_cents,
            storage_location=data.storage_location,
            notes=data.notes,
        )
        kit.tags = data.tags

        saved = self._repository.add(kit)
        self._events.publish(
            KitAdded(kit_id=saved.id, name=saved.name, created_at=saved.created_at)
        )
        return KitRead.model_validate(saved)

    def update_kit(self, kit_id: str, data: KitCreate) -> KitRead:
        """Apply edits to an existing kit and publish :class:`KitUpdated`.

        Raises:
            KitNotFoundError: If ``kit_id`` does not exist.
        """
        existing = self._repository.get(kit_id)
        if existing is None:
            raise KitNotFoundError(kit_id)

        existing.manufacturer = data.manufacturer
        existing.name = data.name
        existing.grade = data.grade
        existing.scale = data.scale
        existing.mobile_suit_designation = data.mobile_suit_designation
        existing.product_number = data.product_number
        existing.series = data.series
        existing.release_year = data.release_year
        existing.status = data.status.value
        existing.priority = data.priority
        existing.difficulty_estimate = data.difficulty_estimate
        existing.estimated_build_hours = data.estimated_build_hours
        existing.purchase_date = data.purchase_date
        existing.purchase_price_cents = data.purchase_price_cents
        existing.storage_location = data.storage_location
        existing.notes = data.notes
        existing.tags = data.tags
        existing.version += 1

        saved = self._repository.update(existing)
        self._events.publish(KitUpdated(kit_id=saved.id, updated_at=saved.updated_at))
        return KitRead.model_validate(saved)

    def archive_kit(self, kit_id: str) -> None:
        """Soft-delete a kit, publishing :class:`KitArchived`.

        Raises:
            KitNotFoundError: If ``kit_id`` does not exist.
        """
        existing = self._repository.get(kit_id)
        if existing is None:
            raise KitNotFoundError(kit_id)
        existing.deleted_at = datetime.now(UTC)
        self._repository.update(existing)
        self._events.publish(KitArchived(kit_id=kit_id))

    def restore_kit(self, kit_id: str) -> KitRead:
        """Clear a kit's soft-deletion.

        Raises:
            KitNotFoundError: If ``kit_id`` does not exist.
        """
        existing = self._repository.get(kit_id)
        if existing is None:
            raise KitNotFoundError(kit_id)
        existing.deleted_at = None
        saved = self._repository.update(existing)
        return KitRead.model_validate(saved)

    def get_kit(self, kit_id: str) -> KitRead:
        """Fetch a single kit.

        Raises:
            KitNotFoundError: If ``kit_id`` does not exist.
        """
        existing = self._repository.get(kit_id)
        if existing is None:
            raise KitNotFoundError(kit_id)
        return KitRead.model_validate(existing)

    def list_kits(self, *, include_archived: bool = False) -> list[KitRead]:
        """List kits, excluding archived ones by default."""
        kits = self._repository.list_all(include_archived=include_archived)
        return [KitRead.model_validate(kit) for kit in kits]

    def count_active_kits(self) -> int:
        """The number of non-archived kits, for dashboard widgets."""
        return self._repository.count_active()
