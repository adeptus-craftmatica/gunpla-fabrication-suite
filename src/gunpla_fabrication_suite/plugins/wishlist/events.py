"""Domain events published by the Wishlist plugin.

Other plugins subscribe to these instead of importing Wishlist's repository
or ORM model — this is the stable, cross-plugin contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class WishlistItemAdded:
    """A new item was added to the wishlist."""

    item_id: str
    name: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class WishlistItemUpdated:
    """An existing wishlist item's fields changed."""

    item_id: str
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class WishlistItemArchived:
    """A wishlist item was soft-deleted (archived) — the builder changed their mind."""

    item_id: str


@dataclass(frozen=True, slots=True)
class WishlistItemPurchased:
    """A wishlist item was marked as purchased."""

    item_id: str
    item_type: str
    purchased_at: datetime
