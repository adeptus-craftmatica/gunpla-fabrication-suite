"""An embeddable photo gallery for one entity: grid, drag-and-drop import, actions.

Designed to be dropped into any plugin's detail view (e.g. Build Planner's
``BuildDetailView``) — it only needs an ``entity_type``/``entity_id`` pair,
never a direct reference to the owning plugin's models.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from gunpla_fabrication_suite.core.jobs import BackgroundJobManager
from gunpla_fabrication_suite.core.jobs.manager import ProgressReporter
from gunpla_fabrication_suite.core.notifications import NotificationCenter, NotificationSeverity
from gunpla_fabrication_suite.plugins.photography.schemas import AttachedPhotoRead, PhotoRead
from gunpla_fabrication_suite.plugins.photography.services.photo_service import PhotoService
from gunpla_fabrication_suite.plugins.photography.ui.comparison_dialog import ComparisonDialog
from gunpla_fabrication_suite.plugins.photography.ui.lightbox_dialog import LightboxDialog
from gunpla_fabrication_suite.plugins.photography.ui.pixmap_utils import (
    IMAGE_EXTENSIONS,
    IMAGE_FILE_FILTER,
)
from gunpla_fabrication_suite.plugins.photography.ui.thumbnail_widget import PhotoThumbnailWidget
from gunpla_fabrication_suite.shared_ui import (
    Card,
    EmptyStateWidget,
    confirm_destructive_action,
    set_button_kind,
)

_COLUMNS = 4


def _bind_attached(
    callback: Callable[[AttachedPhotoRead], None], attached: AttachedPhotoRead
) -> Callable[[PhotoRead], None]:
    """Adapt an ``AttachedPhotoRead`` callback to the thumbnail's ``PhotoRead`` signature.

    A plain lambda with a default-argument capture (``lambda _p, a=attached: ...``)
    would also dodge the late-binding-in-a-loop bug, but this factory function
    keeps each callback's captured ``attached`` in its own explicit, typed scope.
    """

    def _handler(_photo: PhotoRead) -> None:
        callback(attached)

    return _handler


class PhotoGalleryWidget(QWidget):
    """A grid of photos attached to one entity, with import, hero, and delete actions."""

    def __init__(
        self,
        *,
        photo_service: PhotoService,
        jobs: BackgroundJobManager,
        notifications: NotificationCenter,
        entity_type: str,
        entity_id: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._photo_service = photo_service
        self._jobs = jobs
        self._notifications = notifications
        self._entity_type = entity_type
        self._entity_id = entity_id
        self._photos: list[AttachedPhotoRead] = []
        self._pending_job_id: str | None = None

        self.setAcceptDrops(True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        # No header label here: this widget is always embedded under a tab
        # or section that already names it "Photos" — repeating that title
        # inline just above the grid would be redundant.

        header_row = QHBoxLayout()
        header_row.addStretch(1)

        self._compare_button = QPushButton("Compare Before/After")
        set_button_kind(self._compare_button, "secondary")
        self._compare_button.clicked.connect(self._on_compare)
        header_row.addWidget(self._compare_button)

        add_button = QPushButton("Add Photos")
        set_button_kind(add_button, "primary")
        add_button.clicked.connect(self._on_add_photos)
        header_row.addWidget(add_button)
        outer.addLayout(header_row)

        stack_container = QWidget()
        self._stack = QStackedLayout(stack_container)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("QScrollArea { border: none; }")
        self._grid_host = QWidget()
        self._grid = QGridLayout(self._grid_host)
        self._grid.setSpacing(8)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._scroll.setWidget(self._grid_host)
        self._stack.addWidget(self._scroll)

        self._empty_state = EmptyStateWidget(
            title="No photos yet",
            description="Drag photos in, or use Add Photos to import progress pictures.",
            action_label="Add Photos",
            on_action=self._on_add_photos,
        )
        self._stack.addWidget(self._empty_state)

        card = Card()
        card.add_widget(stack_container, stretch=1)
        outer.addWidget(card, 1)

        jobs.job_succeeded.connect(self._on_job_succeeded)
        jobs.job_failed.connect(self._on_job_failed)

        self.refresh()

    def refresh(self) -> None:
        """Reload this entity's photos from the database."""
        self._photos = self._photo_service.list_photos_for_entity(
            self._entity_type, self._entity_id
        )
        self._compare_button.setEnabled(len(self._photos) >= 2)
        self._rebuild_grid()

    def _rebuild_grid(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                # setParent(None) detaches it from rendering immediately;
                # deleteLater() alone leaves it visible until the event loop
                # gets around to destroying it.
                widget.setParent(None)
                widget.deleteLater()

        if not self._photos:
            self._stack.setCurrentWidget(self._empty_state)
            return
        self._stack.setCurrentWidget(self._scroll)

        for index, attached in enumerate(self._photos):
            row, column = divmod(index, _COLUMNS)
            thumb = PhotoThumbnailWidget(
                attached.photo,
                self._photo_service,
                is_hero=attached.is_hero,
                on_activate=_bind_attached(self._open_lightbox, attached),
                on_delete=_bind_attached(self._delete, attached),
                on_set_hero=_bind_attached(self._set_hero, attached),
                on_detach=_bind_attached(self._detach, attached),
            )
            self._grid.addWidget(thumb, row, column)

    def _on_add_photos(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Add Photos", "", IMAGE_FILE_FILTER)
        if paths:
            self._import_paths([Path(path) for path in paths])

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [
            Path(url.toLocalFile())
            for url in event.mimeData().urls()
            if url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() in IMAGE_EXTENSIONS
        ]
        if paths:
            self._import_paths(paths)
            event.acceptProposedAction()

    def _import_paths(self, paths: list[Path]) -> None:
        entity_type = self._entity_type
        entity_id = self._entity_id
        photo_service = self._photo_service

        def _job(report_progress: ProgressReporter) -> list[PhotoRead]:
            return photo_service.import_photos(
                paths, entity_type=entity_type, entity_id=entity_id, report_progress=report_progress
            )

        handle = self._jobs.submit("Importing photos", _job)
        self._pending_job_id = handle.id

    def _on_job_succeeded(self, job_id: str, result: object) -> None:
        if job_id != self._pending_job_id:
            return
        self._pending_job_id = None
        self.refresh()
        count = len(result) if isinstance(result, list) else 0
        self._notifications.post(
            f"Imported {count} photo{'s' if count != 1 else ''}.",
            severity=NotificationSeverity.SUCCESS,
            source="photography",
        )

    def _on_job_failed(self, job_id: str, error: str) -> None:
        if job_id != self._pending_job_id:
            return
        self._pending_job_id = None
        self._notifications.post(
            f"Photo import failed: {error}",
            severity=NotificationSeverity.ERROR,
            source="photography",
        )

    def _open_lightbox(self, attached: AttachedPhotoRead) -> None:
        photos = [item.photo for item in self._photos]
        index = next(
            i for i, item in enumerate(self._photos) if item.photo.id == attached.photo.id
        )
        dialog = LightboxDialog(
            photos,
            index,
            self._photo_service,
            self._notifications,
            on_changed=self.refresh,
            parent=self,
        )
        dialog.exec()

    def _on_compare(self) -> None:
        dialog = ComparisonDialog(
            [item.photo for item in self._photos], self._photo_service, parent=self
        )
        dialog.exec()

    def _set_hero(self, attached: AttachedPhotoRead) -> None:
        self._photo_service.set_hero(attached.relationship_id)
        self.refresh()

    def _detach(self, attached: AttachedPhotoRead) -> None:
        if confirm_destructive_action(
            self,
            title="Remove Photo",
            message="Remove this photo from this build? It will remain in your Photo Library.",
            confirm_label="Remove",
        ):
            self._photo_service.detach(attached.relationship_id)
            self.refresh()

    def _delete(self, attached: AttachedPhotoRead) -> None:
        other_count = self._photo_service.count_relationships(attached.photo.id) - 1
        warning = (
            f" It is also used in {other_count} other place(s) and will be removed from there too."
            if other_count > 0
            else ""
        )
        if confirm_destructive_action(
            self,
            title="Delete Photo",
            message=f"Permanently delete this photo?{warning} This cannot be undone.",
            confirm_label="Delete Permanently",
        ):
            self._photo_service.delete_photo(attached.photo.id)
            self.refresh()
