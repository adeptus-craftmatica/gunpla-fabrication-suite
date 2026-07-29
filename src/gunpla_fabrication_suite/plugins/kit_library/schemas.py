"""Pydantic DTOs for the Kit Library service boundary.

UI code and (eventually) importers/exporters talk to the service through
these schemas, never through the SQLAlchemy model directly.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from gunpla_fabrication_suite.plugins.kit_library.models.kit import CollectionStatus


class KitCreate(BaseModel):
    """Fields required to add a new kit."""

    manufacturer: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=200)
    grade: str = Field(min_length=1, max_length=40)
    scale: str | None = None
    mobile_suit_designation: str | None = None
    product_number: str | None = None
    series: str | None = None
    release_year: int | None = None
    status: CollectionStatus = CollectionStatus.WISHLIST
    priority: int = 0
    difficulty_estimate: int | None = None
    estimated_build_hours: float | None = None
    purchase_date: date | None = None
    purchase_price_cents: int | None = None
    storage_location: str | None = None
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None


class KitRead(BaseModel):
    """A kit as returned to the UI layer."""

    model_config = {"from_attributes": True}

    id: str
    manufacturer: str
    name: str
    grade: str
    scale: str | None
    mobile_suit_designation: str | None
    product_number: str | None
    series: str | None
    release_year: int | None
    status: str
    priority: int
    difficulty_estimate: int | None
    estimated_build_hours: float | None
    purchase_date: date | None
    purchase_price_cents: int | None
    storage_location: str | None
    tags: list[str]
    notes: str | None
    is_deleted: bool
    version: int
    created_at: datetime
    updated_at: datetime
