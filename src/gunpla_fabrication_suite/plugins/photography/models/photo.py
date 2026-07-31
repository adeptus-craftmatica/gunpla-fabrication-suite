"""The ``Photo`` ORM model: one imported image and its derived files.

Only paths into the managed ``media/`` directory are stored here — never
image bytes. The original file is copied in as-is and never modified;
``thumbnail_relpath``/``preview_relpath`` point at derived JPEGs generated
once at import time (see ``services/media_processor.py``).
"""

from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from gunpla_fabrication_suite.core.persistence.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Photo(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An imported photo: its managed files, hash, and light metadata."""

    __tablename__ = "photography_photos"

    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)

    original_relpath: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_relpath: Mapped[str] = mapped_column(String(500), nullable=False)
    preview_relpath: Mapped[str] = mapped_column(String(500), nullable=False)

    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    rotation_degrees: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    caption: Mapped[str | None] = mapped_column(Text, default=None)
    rating: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    exif_json: Mapped[str | None] = mapped_column(Text, default=None)
