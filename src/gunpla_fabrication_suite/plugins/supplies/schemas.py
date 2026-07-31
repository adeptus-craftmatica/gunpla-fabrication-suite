"""Pydantic DTOs for the Supplies service boundary.

UI code and (eventually) importers/exporters talk to the service through
these schemas, never through the SQLAlchemy model directly.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from gunpla_fabrication_suite.plugins.supplies.models.supply import SupplyCategory


class SupplyCreate(BaseModel):
    """Fields required to add a new supply."""

    category: SupplyCategory = SupplyCategory.PAINT
    brand: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=200)
    color_name: str | None = None
    color_hex: str | None = None
    quantity_on_hand: float = 0.0
    unit: str = Field(default="bottle", min_length=1, max_length=20)
    low_stock_threshold: float | None = None
    purchase_date: date | None = None
    purchase_price_cents: int | None = None
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None


class SupplyRead(BaseModel):
    """A supply as returned to the UI layer."""

    model_config = {"from_attributes": True}

    id: str
    category: str
    brand: str
    name: str
    color_name: str | None
    color_hex: str | None
    quantity_on_hand: float
    unit: str
    low_stock_threshold: float | None
    purchase_date: date | None
    purchase_price_cents: int | None
    tags: list[str]
    notes: str | None
    is_low_stock: bool
    is_deleted: bool
    version: int
    created_at: datetime
    updated_at: datetime
