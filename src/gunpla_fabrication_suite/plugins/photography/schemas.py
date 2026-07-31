"""Pydantic DTOs for the Photography service boundary."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PhotoRead(BaseModel):
    """A photo as returned to the UI layer, with EXIF parsed into a dict."""

    model_config = {"from_attributes": True}

    id: str
    sha256_hash: str
    original_filename: str
    source_path: str
    original_relpath: str
    thumbnail_relpath: str
    preview_relpath: str
    width: int
    height: int
    file_size_bytes: int
    rotation_degrees: int
    caption: str | None
    rating: int
    exif: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, photo: Any) -> PhotoRead:
        """Build from a ``Photo`` ORM instance, parsing its stored EXIF JSON."""
        return cls(
            id=photo.id,
            sha256_hash=photo.sha256_hash,
            original_filename=photo.original_filename,
            source_path=photo.source_path,
            original_relpath=photo.original_relpath,
            thumbnail_relpath=photo.thumbnail_relpath,
            preview_relpath=photo.preview_relpath,
            width=photo.width,
            height=photo.height,
            file_size_bytes=photo.file_size_bytes,
            rotation_degrees=photo.rotation_degrees,
            caption=photo.caption,
            rating=photo.rating,
            exif=json.loads(photo.exif_json) if photo.exif_json else {},
            created_at=photo.created_at,
            updated_at=photo.updated_at,
        )


class AttachedPhotoRead(BaseModel):
    """A photo together with the relationship that attaches it to an entity."""

    model_config = {"from_attributes": True}

    relationship_id: str
    photo: PhotoRead
    entity_type: str
    entity_id: str
    is_hero: bool
    order_index: int
