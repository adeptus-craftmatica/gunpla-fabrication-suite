"""The ``Kit`` ORM model: a single entry in a builder's collection or backlog."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from sqlalchemy import Date, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from gunpla_fabrication_suite.core.persistence.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    VersionMixin,
)


class CollectionStatus(StrEnum):
    """Where a kit sits in the collection-to-completed lifecycle.

    Stored as plain text rather than a native SQL enum so statuses can
    become user-customizable in a future milestone without a schema change.
    """

    WISHLIST = "wishlist"
    PREORDERED = "preordered"
    ORDERED = "ordered"
    IN_TRANSIT = "in_transit"
    OWNED_SEALED = "owned_sealed"
    OPENED = "opened"
    PARTS_CHECKED = "parts_checked"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    WAITING_ON_SUPPLIES = "waiting_on_supplies"
    WAITING_ON_REPLACEMENT_PARTS = "waiting_on_replacement_parts"
    COMPLETED = "completed"
    DISPLAYED = "displayed"
    STORED = "stored"
    SOLD = "sold"
    GIFTED = "gifted"
    ABANDONED = "abandoned"


class Kit(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    """A kit owned or wanted by the builder."""

    __tablename__ = "kit_library_kits"

    manufacturer: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    grade: Mapped[str] = mapped_column(String(40), nullable=False)
    scale: Mapped[str | None] = mapped_column(String(20), default=None)
    mobile_suit_designation: Mapped[str | None] = mapped_column(String(80), default=None)
    product_number: Mapped[str | None] = mapped_column(String(60), default=None)
    series: Mapped[str | None] = mapped_column(String(120), default=None)
    release_year: Mapped[int | None] = mapped_column(Integer, default=None)

    status: Mapped[str] = mapped_column(
        String(40), nullable=False, default=CollectionStatus.WISHLIST.value
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    difficulty_estimate: Mapped[int | None] = mapped_column(Integer, default=None)
    estimated_build_hours: Mapped[float | None] = mapped_column(default=None)

    purchase_date: Mapped[date | None] = mapped_column(Date, default=None)
    purchase_price_cents: Mapped[int | None] = mapped_column(Integer, default=None)
    storage_location: Mapped[str | None] = mapped_column(String(120), default=None)

    tags_csv: Mapped[str | None] = mapped_column(Text, default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)

    @property
    def tags(self) -> list[str]:
        """Tags as a list, parsed from the stored comma-separated text."""
        if not self.tags_csv:
            return []
        return [tag.strip() for tag in self.tags_csv.split(",") if tag.strip()]

    @tags.setter
    def tags(self, value: list[str]) -> None:
        self.tags_csv = ", ".join(tag.strip() for tag in value if tag.strip()) or None
