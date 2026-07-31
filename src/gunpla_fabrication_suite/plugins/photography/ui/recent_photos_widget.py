"""The "Recent Photos" dashboard widget: a strip of the most recently imported photos."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from gunpla_fabrication_suite.plugins.photography.services.photo_service import PhotoService
from gunpla_fabrication_suite.plugins.photography.ui.pixmap_utils import load_rotated_pixmap
from gunpla_fabrication_suite.shared_ui import EmptyStateWidget, set_label_role

_RECENT_COUNT = 6
_THUMBNAIL_SIZE = 64


class RecentPhotosWidget(QWidget):
    """Shows thumbnails of the most recently imported photos, newest first."""

    def __init__(self, photo_service: PhotoService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)

        photos = photo_service.list_all_photos(limit=_RECENT_COUNT)
        if not photos:
            layout.addWidget(
                EmptyStateWidget(
                    title="No photos yet",
                    description="Import progress photos from a build's gallery.",
                )
            )
            return

        strip = QHBoxLayout()
        strip.setSpacing(6)
        for photo in photos:
            pixmap = load_rotated_pixmap(
                photo_service.resolve_thumbnail_path(photo), photo.rotation_degrees
            )
            if not pixmap.isNull():
                pixmap = pixmap.scaled(
                    QSize(_THUMBNAIL_SIZE, _THUMBNAIL_SIZE),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            image_label = QLabel()
            image_label.setPixmap(pixmap)
            image_label.setFixedSize(_THUMBNAIL_SIZE, _THUMBNAIL_SIZE)
            image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # Reuses the same #photoThumbnailImage rule as the gallery grid's
            # thumbnails (see thumbnail_widget.py) — same look, no "hero"
            # property set since this strip doesn't distinguish hero photos.
            image_label.setObjectName("photoThumbnailImage")
            strip.addWidget(image_label)
        strip.addStretch(1)
        layout.addLayout(strip)

        count_label = QLabel(f"{len(photos)} recent photo{'s' if len(photos) != 1 else ''}")
        set_label_role(count_label, "secondary")
        layout.addWidget(count_label)
