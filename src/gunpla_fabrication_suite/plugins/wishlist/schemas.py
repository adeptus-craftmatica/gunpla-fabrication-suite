"""Pydantic DTOs for the Wishlist service boundary.

UI code and (eventually) importers/exporters talk to the service through
these schemas, never through the SQLAlchemy model directly.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from gunpla_fabrication_suite.plugins.wishlist.models.wishlist_item import WishlistItemType


class WishlistItemCreate(BaseModel):
    """Fields required to add a new wishlist item."""

    item_type: WishlistItemType = WishlistItemType.OTHER
    name: str = Field(min_length=1, max_length=200)
    manufacturer: str | None = None
    priority: int = 0
    estimated_price_cents: int | None = None
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None


class WishlistItemRead(BaseModel):
    """A wishlist item as returned to the UI layer."""

    model_config = {"from_attributes": True}

    id: str
    item_type: str
    name: str
    manufacturer: str | None
    priority: int
    estimated_price_cents: int | None
    tags: list[str]
    notes: str | None
    is_purchased: bool
    purchased_at: datetime | None
    is_deleted: bool
    version: int
    created_at: datetime
    updated_at: datetime
