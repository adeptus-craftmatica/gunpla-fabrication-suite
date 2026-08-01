"""The ``WishlistItem`` ORM model: a kit, tool, paint, or part the builder wants to buy."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from gunpla_fabrication_suite.core.persistence.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    VersionMixin,
)
from gunpla_fabrication_suite.core.persistence.types import UTCDateTime


class WishlistItemType(StrEnum):
    """What kind of thing a wishlist item is.

    Stored as plain text rather than a native SQL enum so types can become
    user-customizable in a future milestone without a schema change.
    """

    KIT = "kit"
    TOOL = "tool"
    PAINT = "paint"
    PART = "part"
    OTHER = "other"


class WishlistItem(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    """A kit, tool, paint, or part the builder wants to buy but doesn't own yet."""

    __tablename__ = "wishlist_items"

    item_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=WishlistItemType.OTHER.value
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    manufacturer: Mapped[str | None] = mapped_column(String(120), default=None)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_price_cents: Mapped[int | None] = mapped_column(Integer, default=None)

    tags_csv: Mapped[str | None] = mapped_column(Text, default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)

    is_purchased: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    purchased_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)

    @property
    def tags(self) -> list[str]:
        """Tags as a list, parsed from the stored comma-separated text."""
        if not self.tags_csv:
            return []
        return [tag.strip() for tag in self.tags_csv.split(",") if tag.strip()]

    @tags.setter
    def tags(self, value: list[str]) -> None:
        self.tags_csv = ", ".join(tag.strip() for tag in value if tag.strip()) or None
