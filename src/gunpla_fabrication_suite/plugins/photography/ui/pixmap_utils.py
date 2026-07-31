"""Shared pixmap-loading helpers for the Photography UI."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QPixmap, QTransform

IMAGE_FILE_FILTER = "Images (*.jpg *.jpeg *.png *.bmp *.gif *.webp *.tif *.tiff)"
IMAGE_EXTENSIONS = frozenset(
    {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff"}
)


def load_rotated_pixmap(path: Path, rotation_degrees: int) -> QPixmap:
    """Load an image file, applying the user's manual display rotation, if any.

    EXIF orientation is already baked into the derived thumbnail/preview
    files at import time (see ``services/media_processor.py``); this handles
    the separate, user-driven rotation stored on the photo itself.
    """
    pixmap = QPixmap(str(path))
    if pixmap.isNull() or rotation_degrees % 360 == 0:
        return pixmap
    return pixmap.transformed(QTransform().rotate(rotation_degrees))
