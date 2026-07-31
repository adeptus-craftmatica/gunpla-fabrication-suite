"""The ``PhotoRelationship`` ORM model: a polymorphic link from a photo to any entity.

``entity_type`` + ``entity_id`` intentionally has no SQL foreign key —
Photography must not depend on (or import) any other plugin's tables. Any
plugin that wants photos on its own records attaches them through
``PhotoService`` using a well-known ``PhotoEntityType`` value plus its own
record's id.
"""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from gunpla_fabrication_suite.core.persistence.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class PhotoRelationship(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Links one photo to one entity, with an optional per-entity hero flag."""

    __tablename__ = "photography_photo_relationships"

    photo_id: Mapped[str] = mapped_column(
        ForeignKey("photography_photos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    is_hero: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
