"""Domain events published by the Photography plugin.

Other plugins subscribe to these instead of importing Photography's
repository or ORM models directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class PhotoImported:
    """A new photo was imported into managed storage."""

    photo_id: str
    original_filename: str
    imported_at: datetime


@dataclass(frozen=True, slots=True)
class PhotoAttached:
    """A photo was linked to an entity."""

    photo_id: str
    entity_type: str
    entity_id: str


@dataclass(frozen=True, slots=True)
class PhotoDetached:
    """A photo was unlinked from an entity."""

    photo_id: str
    entity_type: str
    entity_id: str


@dataclass(frozen=True, slots=True)
class PhotoDeleted:
    """A photo and its managed files were permanently removed."""

    photo_id: str
