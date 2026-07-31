"""The ``Supply`` ORM model: a single paint, cement, tool, or other hobby supply."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from sqlalchemy import Date, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from gunpla_fabrication_suite.core.persistence.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    VersionMixin,
)


class SupplyCategory(StrEnum):
    """What kind of hobby supply an item is.

    Stored as plain text rather than a native SQL enum so categories can
    become user-customizable in a future milestone without a schema change.
    """

    PAINT = "paint"
    PRIMER = "primer"
    TOPCOAT = "topcoat"
    CEMENT = "cement"
    PUTTY = "putty"
    DECAL = "decal"
    TOOL = "tool"
    OTHER = "other"


class Supply(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    """A paint, cement, tool, or other hobby supply the builder owns."""

    __tablename__ = "supplies_items"

    category: Mapped[str] = mapped_column(
        String(40), nullable=False, default=SupplyCategory.PAINT.value
    )
    brand: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    color_name: Mapped[str | None] = mapped_column(String(120), default=None)
    color_hex: Mapped[str | None] = mapped_column(String(7), default=None)

    quantity_on_hand: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="bottle")
    low_stock_threshold: Mapped[float | None] = mapped_column(Float, default=None)

    purchase_date: Mapped[date | None] = mapped_column(Date, default=None)
    purchase_price_cents: Mapped[int | None] = mapped_column(Integer, default=None)

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

    @property
    def is_low_stock(self) -> bool:
        """Whether quantity has dropped to or below the configured threshold.

        Always ``False`` when no threshold is set — an unset threshold means
        the builder hasn't opted this item into low-stock tracking.
        """
        if self.low_stock_threshold is None:
            return False
        return self.quantity_on_hand <= self.low_stock_threshold
