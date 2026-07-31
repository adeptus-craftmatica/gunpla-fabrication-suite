"""A single photo cell in a gallery grid: thumbnail, rating, hero badge, context menu."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QContextMenuEvent, QMouseEvent
from PySide6.QtWidgets import QLabel, QMenu, QVBoxLayout, QWidget

from gunpla_fabrication_suite.plugins.photography.schemas import PhotoRead
from gunpla_fabrication_suite.plugins.photography.services.photo_service import PhotoService
from gunpla_fabrication_suite.plugins.photography.ui.pixmap_utils import load_rotated_pixmap
from gunpla_fabrication_suite.shared_ui import set_label_role

CELL_SIZE = 140
_IMAGE_SIZE = 116


class PhotoThumbnailWidget(QWidget):
    """One clickable, right-clickable photo cell.

    Reused by both the entity-scoped gallery (which offers hero/detach
    actions on top of the universal view/delete) and the global Photo
    Library page (view/delete only) — pass ``on_set_hero``/``on_detach`` as
    ``None`` to omit those menu entries.
    """

    def __init__(
        self,
        photo: PhotoRead,
        photo_service: PhotoService,
        *,
        is_hero: bool = False,
        on_activate: Callable[[PhotoRead], None],
        on_delete: Callable[[PhotoRead], None],
        on_set_hero: Callable[[PhotoRead], None] | None = None,
        on_detach: Callable[[PhotoRead], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._photo = photo
        self._is_hero = is_hero
        self._on_activate = on_activate
        self._on_delete = on_delete
        self._on_set_hero = on_set_hero
        self._on_detach = on_detach

        self.setFixedSize(CELL_SIZE, CELL_SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(photo.caption or photo.original_filename)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        image_label = QLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setFixedSize(_IMAGE_SIZE, _IMAGE_SIZE)
        pixmap = load_rotated_pixmap(
            photo_service.resolve_thumbnail_path(photo), photo.rotation_degrees
        )
        if not pixmap.isNull():
            pixmap = pixmap.scaled(
                QSize(_IMAGE_SIZE, _IMAGE_SIZE),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        image_label.setPixmap(pixmap)
        image_label.setObjectName("photoThumbnailImage")
        image_label.setProperty("hero", is_hero)
        layout.addWidget(image_label)

        caption_bits = ["★ Hero" if is_hero else ""]
        if photo.rating:
            caption_bits.append("★" * photo.rating)
        caption_label = QLabel(" · ".join(bit for bit in caption_bits if bit))
        caption_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        set_label_role(caption_label, "caption")
        layout.addWidget(caption_label)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_activate(self._photo)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        menu = QMenu(self)
        menu.addAction("View", lambda: self._on_activate(self._photo))

        on_set_hero = self._on_set_hero
        if on_set_hero is not None and not self._is_hero:
            menu.addAction("Set as Hero", lambda: on_set_hero(self._photo))

        on_detach = self._on_detach
        if on_detach is not None:
            menu.addAction("Remove from this Build", lambda: on_detach(self._photo))

        menu.addSeparator()
        delete_action = menu.addAction("Delete Permanently")
        delete_action.triggered.connect(lambda: self._on_delete(self._photo))
        menu.exec(event.globalPos())
