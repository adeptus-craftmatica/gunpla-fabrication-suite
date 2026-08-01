"""Tests for Wishlist business logic: creation, editing, archiving, and purchasing."""

from __future__ import annotations

import pytest

from gunpla_fabrication_suite.core.events import EventBus
from gunpla_fabrication_suite.core.persistence import DatabaseService
from gunpla_fabrication_suite.plugins.wishlist.events import (
    WishlistItemAdded,
    WishlistItemArchived,
    WishlistItemPurchased,
    WishlistItemUpdated,
)
from gunpla_fabrication_suite.plugins.wishlist.models.wishlist_item import WishlistItemType
from gunpla_fabrication_suite.plugins.wishlist.repositories.wishlist_repository import (
    WishlistRepository,
)
from gunpla_fabrication_suite.plugins.wishlist.schemas import WishlistItemCreate
from gunpla_fabrication_suite.plugins.wishlist.services.wishlist_service import (
    WishlistItemNotFoundError,
    WishlistService,
)


@pytest.fixture
def wishlist_service(database: DatabaseService, event_bus: EventBus) -> WishlistService:
    return WishlistService(WishlistRepository(database), event_bus)


def _create_payload(**overrides: object) -> WishlistItemCreate:
    defaults: dict[str, object] = {"name": "RX-78-2 Gundam"}
    defaults.update(overrides)
    return WishlistItemCreate(**defaults)  # type: ignore[arg-type]


def test_create_item_persists_and_returns_it(wishlist_service: WishlistService) -> None:
    created = wishlist_service.create_item(_create_payload())

    assert created.name == "RX-78-2 Gundam"
    assert created.id
    assert created.is_purchased is False

    listed = wishlist_service.list_items()
    assert [item.id for item in listed] == [created.id]


def test_create_item_publishes_wishlist_item_added_event(
    wishlist_service: WishlistService, event_bus: EventBus
) -> None:
    events: list[WishlistItemAdded] = []
    event_bus.subscribe(WishlistItemAdded, events.append)

    created = wishlist_service.create_item(_create_payload())

    assert len(events) == 1
    assert events[0].item_id == created.id


def test_update_item_changes_fields_and_publishes_event(
    wishlist_service: WishlistService, event_bus: EventBus
) -> None:
    events: list[WishlistItemUpdated] = []
    event_bus.subscribe(WishlistItemUpdated, events.append)
    created = wishlist_service.create_item(_create_payload())

    updated = wishlist_service.update_item(created.id, _create_payload(priority=4))

    assert updated.priority == 4
    assert updated.version == created.version + 1
    assert len(events) == 1


def test_update_item_raises_for_unknown_id(wishlist_service: WishlistService) -> None:
    with pytest.raises(WishlistItemNotFoundError):
        wishlist_service.update_item("missing-id", _create_payload())


def test_archive_item_hides_it_from_default_listing(
    wishlist_service: WishlistService, event_bus: EventBus
) -> None:
    events: list[WishlistItemArchived] = []
    event_bus.subscribe(WishlistItemArchived, events.append)
    created = wishlist_service.create_item(_create_payload())

    wishlist_service.archive_item(created.id)

    assert wishlist_service.list_items() == []
    assert wishlist_service.list_items(include_archived=True)[0].is_deleted is True
    assert len(events) == 1


def test_restore_item_makes_it_visible_again(wishlist_service: WishlistService) -> None:
    created = wishlist_service.create_item(_create_payload())
    wishlist_service.archive_item(created.id)

    restored = wishlist_service.restore_item(created.id)

    assert restored.is_deleted is False
    assert [item.id for item in wishlist_service.list_items()] == [created.id]


def test_archive_item_raises_for_unknown_id(wishlist_service: WishlistService) -> None:
    with pytest.raises(WishlistItemNotFoundError):
        wishlist_service.archive_item("missing-id")


def test_count_active_items_reflects_archival(wishlist_service: WishlistService) -> None:
    first = wishlist_service.create_item(_create_payload(name="First"))
    wishlist_service.create_item(_create_payload(name="Second"))

    assert wishlist_service.count_active_items() == 2

    wishlist_service.archive_item(first.id)

    assert wishlist_service.count_active_items() == 1


def test_mark_purchased_sets_flag_and_timestamp(wishlist_service: WishlistService) -> None:
    created = wishlist_service.create_item(_create_payload())

    purchased = wishlist_service.mark_purchased(created.id)

    assert purchased.is_purchased is True
    assert purchased.purchased_at is not None
    assert purchased.version == created.version + 1


def test_mark_purchased_publishes_wishlist_item_purchased_event(
    wishlist_service: WishlistService, event_bus: EventBus
) -> None:
    events: list[WishlistItemPurchased] = []
    event_bus.subscribe(WishlistItemPurchased, events.append)
    created = wishlist_service.create_item(_create_payload(item_type=WishlistItemType.KIT))

    wishlist_service.mark_purchased(created.id)

    assert len(events) == 1
    assert events[0].item_id == created.id
    assert events[0].item_type == "kit"


def test_mark_purchased_raises_for_unknown_id(wishlist_service: WishlistService) -> None:
    with pytest.raises(WishlistItemNotFoundError):
        wishlist_service.mark_purchased("missing-id")


def test_purchased_items_excluded_from_default_listing(wishlist_service: WishlistService) -> None:
    created = wishlist_service.create_item(_create_payload())
    wishlist_service.mark_purchased(created.id)

    assert wishlist_service.list_items() == []
    assert wishlist_service.count_active_items() == 0
    listed_with_purchased = wishlist_service.list_items(include_purchased=True)
    assert [item.id for item in listed_with_purchased] == [created.id]
    assert listed_with_purchased[0].is_purchased is True
