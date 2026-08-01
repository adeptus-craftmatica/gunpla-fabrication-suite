"""Business logic for managing the wishlist: the only entry point the UI should use."""

from __future__ import annotations

from datetime import UTC, datetime

from gunpla_fabrication_suite.core.events import EventBus
from gunpla_fabrication_suite.plugins.wishlist.events import (
    WishlistItemAdded,
    WishlistItemArchived,
    WishlistItemPurchased,
    WishlistItemUpdated,
)
from gunpla_fabrication_suite.plugins.wishlist.models.wishlist_item import WishlistItem
from gunpla_fabrication_suite.plugins.wishlist.repositories.wishlist_repository import (
    WishlistRepository,
)
from gunpla_fabrication_suite.plugins.wishlist.schemas import WishlistItemCreate, WishlistItemRead


class WishlistItemNotFoundError(LookupError):
    """Raised when an operation targets a wishlist item id that does not exist."""

    def __init__(self, item_id: str) -> None:
        super().__init__(f"No wishlist item found with id {item_id!r}")
        self.item_id = item_id


class WishlistService:
    """Validates, persists, and publishes events for wishlist changes."""

    def __init__(self, repository: WishlistRepository, events: EventBus) -> None:
        self._repository = repository
        self._events = events

    def create_item(self, data: WishlistItemCreate) -> WishlistItemRead:
        """Add a new wishlist item and publish :class:`WishlistItemAdded`."""
        item = WishlistItem(
            item_type=data.item_type.value,
            name=data.name,
            manufacturer=data.manufacturer,
            priority=data.priority,
            estimated_price_cents=data.estimated_price_cents,
            notes=data.notes,
        )
        item.tags = data.tags

        saved = self._repository.add(item)
        self._events.publish(
            WishlistItemAdded(item_id=saved.id, name=saved.name, created_at=saved.created_at)
        )
        return WishlistItemRead.model_validate(saved)

    def update_item(self, item_id: str, data: WishlistItemCreate) -> WishlistItemRead:
        """Apply edits to an existing wishlist item and publish :class:`WishlistItemUpdated`.

        Raises:
            WishlistItemNotFoundError: If ``item_id`` does not exist.
        """
        existing = self._repository.get(item_id)
        if existing is None:
            raise WishlistItemNotFoundError(item_id)

        existing.item_type = data.item_type.value
        existing.name = data.name
        existing.manufacturer = data.manufacturer
        existing.priority = data.priority
        existing.estimated_price_cents = data.estimated_price_cents
        existing.notes = data.notes
        existing.tags = data.tags
        existing.version += 1

        saved = self._repository.update(existing)
        self._events.publish(WishlistItemUpdated(item_id=saved.id, updated_at=saved.updated_at))
        return WishlistItemRead.model_validate(saved)

    def archive_item(self, item_id: str) -> None:
        """Soft-delete a wishlist item, publishing :class:`WishlistItemArchived`.

        Raises:
            WishlistItemNotFoundError: If ``item_id`` does not exist.
        """
        existing = self._repository.get(item_id)
        if existing is None:
            raise WishlistItemNotFoundError(item_id)
        existing.deleted_at = datetime.now(UTC)
        self._repository.update(existing)
        self._events.publish(WishlistItemArchived(item_id=item_id))

    def restore_item(self, item_id: str) -> WishlistItemRead:
        """Clear a wishlist item's soft-deletion.

        Raises:
            WishlistItemNotFoundError: If ``item_id`` does not exist.
        """
        existing = self._repository.get(item_id)
        if existing is None:
            raise WishlistItemNotFoundError(item_id)
        existing.deleted_at = None
        saved = self._repository.update(existing)
        return WishlistItemRead.model_validate(saved)

    def mark_purchased(self, item_id: str) -> WishlistItemRead:
        """Mark a wishlist item as purchased, publishing :class:`WishlistItemPurchased`.

        There's no ``mark_unpurchased`` — reversing a purchase isn't
        supported in this pass; add a fresh wishlist item instead if needed.

        Raises:
            WishlistItemNotFoundError: If ``item_id`` does not exist.
        """
        existing = self._repository.get(item_id)
        if existing is None:
            raise WishlistItemNotFoundError(item_id)
        purchased_at = datetime.now(UTC)
        existing.is_purchased = True
        existing.purchased_at = purchased_at
        existing.version += 1
        saved = self._repository.update(existing)
        self._events.publish(
            WishlistItemPurchased(
                item_id=saved.id, item_type=saved.item_type, purchased_at=purchased_at
            )
        )
        return WishlistItemRead.model_validate(saved)

    def get_item(self, item_id: str) -> WishlistItemRead:
        """Fetch a single wishlist item.

        Raises:
            WishlistItemNotFoundError: If ``item_id`` does not exist.
        """
        existing = self._repository.get(item_id)
        if existing is None:
            raise WishlistItemNotFoundError(item_id)
        return WishlistItemRead.model_validate(existing)

    def list_items(
        self, *, include_archived: bool = False, include_purchased: bool = False
    ) -> list[WishlistItemRead]:
        """List wishlist items, excluding archived and purchased ones by default."""
        items = self._repository.list_all(
            include_archived=include_archived, include_purchased=include_purchased
        )
        return [WishlistItemRead.model_validate(item) for item in items]

    def count_active_items(self) -> int:
        """The number of items still wanted (not archived, not purchased)."""
        return self._repository.count_active()
