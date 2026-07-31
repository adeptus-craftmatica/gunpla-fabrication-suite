"""Full-size photo viewer with caption/rating/rotation editing and prev/next navigation.

Deliberately universal (works from both the entity-scoped gallery and the
global Photo Library) — it only edits a photo's own fields and offers
permanent delete. Relationship-scoped actions (hero, detach) stay on the
gallery grid's per-thumbnail context menu, since a photo viewed from the
Photo Library isn't necessarily tied to one particular relationship.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gunpla_fabrication_suite.core.notifications import NotificationCenter, NotificationSeverity
from gunpla_fabrication_suite.plugins.photography.schemas import PhotoRead
from gunpla_fabrication_suite.plugins.photography.services.photo_service import PhotoService
from gunpla_fabrication_suite.plugins.photography.ui.pixmap_utils import load_rotated_pixmap
from gunpla_fabrication_suite.shared_ui import confirm_destructive_action, set_button_kind

_PREVIEW_MAX_SIZE = QSize(820, 520)
_RATING_LABELS = ("No rating", "★", "★★", "★★★", "★★★★", "★★★★★")


class LightboxDialog(QDialog):
    """A modal photo viewer for one photo at a time out of a fixed list."""

    def __init__(
        self,
        photos: list[PhotoRead],
        start_index: int,
        photo_service: PhotoService,
        notifications: NotificationCenter,
        *,
        on_changed: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Photo")
        self.resize(900, 700)

        self._photos = list(photos)
        self._index = start_index
        self._photo_service = photo_service
        self._notifications = notifications
        self._on_changed = on_changed
        self._changed = False

        outer = QVBoxLayout(self)

        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setMinimumSize(400, 320)
        outer.addWidget(self._image_label, stretch=1)

        nav_row = QHBoxLayout()
        self._prev_button = QPushButton("< Previous")
        self._prev_button.setAutoDefault(False)
        self._prev_button.clicked.connect(self._show_previous)
        nav_row.addWidget(self._prev_button)
        nav_row.addStretch(1)

        self._rotate_left_button = QPushButton("Rotate Left")
        self._rotate_left_button.setAutoDefault(False)
        self._rotate_left_button.clicked.connect(lambda: self._rotate(-90))
        nav_row.addWidget(self._rotate_left_button)

        self._position_label = QLabel()
        nav_row.addWidget(self._position_label)

        self._rotate_right_button = QPushButton("Rotate Right")
        self._rotate_right_button.setAutoDefault(False)
        self._rotate_right_button.clicked.connect(lambda: self._rotate(90))
        nav_row.addWidget(self._rotate_right_button)

        nav_row.addStretch(1)
        self._next_button = QPushButton("Next >")
        self._next_button.setAutoDefault(False)
        self._next_button.clicked.connect(self._show_next)
        nav_row.addWidget(self._next_button)
        outer.addLayout(nav_row)

        details_row = QHBoxLayout()
        self._caption_edit = QLineEdit()
        self._caption_edit.setPlaceholderText("Add a caption...")
        details_row.addWidget(self._caption_edit, stretch=1)

        self._rating_combo = QComboBox()
        self._rating_combo.addItems(_RATING_LABELS)
        details_row.addWidget(self._rating_combo)

        self._save_button = QPushButton("Save")
        self._save_button.setDefault(True)  # also lets Enter trigger Save
        set_button_kind(self._save_button, "primary")
        self._save_button.clicked.connect(self._save_details)
        details_row.addWidget(self._save_button)
        outer.addLayout(details_row)

        delete_row = QHBoxLayout()
        delete_row.addStretch(1)
        delete_button = QPushButton("Delete Permanently")
        delete_button.setAutoDefault(False)
        set_button_kind(delete_button, "danger")
        delete_button.clicked.connect(self._delete)
        delete_row.addWidget(delete_button)
        outer.addLayout(delete_row)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.button(QDialogButtonBox.StandardButton.Close).setAutoDefault(False)
        button_box.rejected.connect(self.reject)
        outer.addWidget(button_box)

        self._load_current()

    def _current(self) -> PhotoRead:
        return self._photos[self._index]

    def _load_current(self) -> None:
        photo = self._current()
        pixmap = load_rotated_pixmap(
            self._photo_service.resolve_preview_path(photo), photo.rotation_degrees
        )
        if not pixmap.isNull():
            pixmap = pixmap.scaled(
                _PREVIEW_MAX_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        self._image_label.setPixmap(pixmap)

        self._position_label.setText(f"{self._index + 1} of {len(self._photos)}")
        self._prev_button.setEnabled(self._index > 0)
        self._next_button.setEnabled(self._index < len(self._photos) - 1)
        self._caption_edit.setText(photo.caption or "")
        self._rating_combo.setCurrentIndex(photo.rating)

    def _show_previous(self) -> None:
        if self._index > 0:
            self._index -= 1
            self._load_current()

    def _show_next(self) -> None:
        if self._index < len(self._photos) - 1:
            self._index += 1
            self._load_current()

    def _save_details(self) -> None:
        photo = self._current()
        updated = self._photo_service.update_details(
            photo.id,
            caption=self._caption_edit.text().strip() or None,
            rating=self._rating_combo.currentIndex(),
            rotation_degrees=photo.rotation_degrees,
        )
        self._photos[self._index] = updated
        self._changed = True
        self._notifications.post(
            "Photo details saved.", severity=NotificationSeverity.SUCCESS, source="photography"
        )

    def _rotate(self, delta_degrees: int) -> None:
        photo = self._current()
        updated = self._photo_service.update_details(
            photo.id,
            caption=photo.caption,
            rating=photo.rating,
            rotation_degrees=photo.rotation_degrees + delta_degrees,
        )
        self._photos[self._index] = updated
        self._changed = True
        self._load_current()

    def _delete(self) -> None:
        photo = self._current()
        other_count = self._photo_service.count_relationships(photo.id)
        warning = (
            f" It is used in {other_count} place(s) and will be removed from all of them."
            if other_count
            else ""
        )
        if not confirm_destructive_action(
            self,
            title="Delete Photo",
            message=f"Permanently delete this photo?{warning} This cannot be undone.",
            confirm_label="Delete Permanently",
        ):
            return

        self._photo_service.delete_photo(photo.id)
        self._changed = True
        del self._photos[self._index]
        if not self._photos:
            self.accept()
            return
        self._index = min(self._index, len(self._photos) - 1)
        self._load_current()

    def reject(self) -> None:
        if self._changed:
            self._on_changed()
        super().reject()

    def accept(self) -> None:
        if self._changed:
            self._on_changed()
        super().accept()
