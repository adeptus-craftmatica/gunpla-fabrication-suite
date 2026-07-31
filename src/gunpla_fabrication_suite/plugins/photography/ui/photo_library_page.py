"""The global Photo Library nav page: every imported photo, regardless of build."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QPushButton,
    QScrollArea,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from gunpla_fabrication_suite.core.jobs import BackgroundJobManager
from gunpla_fabrication_suite.core.jobs.manager import ProgressReporter
from gunpla_fabrication_suite.core.layout import COMMAND_DECK, LayoutManager
from gunpla_fabrication_suite.core.notifications import NotificationCenter, NotificationSeverity
from gunpla_fabrication_suite.plugins.photography.schemas import PhotoRead
from gunpla_fabrication_suite.plugins.photography.services.photo_service import PhotoService
from gunpla_fabrication_suite.plugins.photography.ui.lightbox_dialog import LightboxDialog
from gunpla_fabrication_suite.plugins.photography.ui.pixmap_utils import (
    IMAGE_EXTENSIONS,
    IMAGE_FILE_FILTER,
)
from gunpla_fabrication_suite.plugins.photography.ui.thumbnail_widget import PhotoThumbnailWidget
from gunpla_fabrication_suite.shared_ui import (
    Card,
    EmptyStateWidget,
    PageHeader,
    confirm_destructive_action,
    set_button_kind,
)

_RAIL_COLUMNS = 6
_COMMAND_DECK_COLUMNS = 9


class PhotoLibraryPage(QWidget):
    """Every photo ever imported, independent of which build (if any) it's attached to."""

    def __init__(
        self,
        *,
        photo_service: PhotoService,
        jobs: BackgroundJobManager,
        notifications: NotificationCenter,
        layout_manager: LayoutManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._photo_service = photo_service
        self._jobs = jobs
        self._notifications = notifications
        self._layout_manager = layout_manager
        self._photos: list[PhotoRead] = []
        self._pending_job_id: str | None = None

        self.setAcceptDrops(True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)

        import_button = QPushButton("Import Photos")
        set_button_kind(import_button, "primary")
        import_button.clicked.connect(self._on_import)
        outer.addWidget(PageHeader("Photo Library", actions=[import_button]))

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
            description="Import progress photos, drag them in, or add them from a build's gallery.",
            action_label="Import Photos",
            on_action=self._on_import,
        )
        self._stack.addWidget(self._empty_state)

        card = Card()
        card.add_widget(stack_container, stretch=1)
        outer.addWidget(card, 1)

        jobs.job_succeeded.connect(self._on_job_succeeded)
        jobs.job_failed.connect(self._on_job_failed)

        layout_manager.layout_changed.connect(self._on_layout_changed)
        self.refresh()

    def _on_layout_changed(self, _layout_id: str) -> None:
        self._rebuild_grid()

    def _columns(self) -> int:
        if self._layout_manager.current == COMMAND_DECK:
            return _COMMAND_DECK_COLUMNS
        return _RAIL_COLUMNS

    def refresh(self) -> None:
        """Reload the full photo library from the database."""
        self._photos = self._photo_service.list_all_photos()
        self._rebuild_grid()

    def _rebuild_grid(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        if not self._photos:
            self._stack.setCurrentWidget(self._empty_state)
            return
        self._stack.setCurrentWidget(self._scroll)

        columns = self._columns()
        for index, photo in enumerate(self._photos):
            row, column = divmod(index, columns)
            thumb = PhotoThumbnailWidget(
                photo,
                self._photo_service,
                on_activate=self._open_lightbox,
                on_delete=self._delete,
            )
            self._grid.addWidget(thumb, row, column)

    def _on_import(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Import Photos", "", IMAGE_FILE_FILTER)
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
        photo_service = self._photo_service

        def _job(report_progress: ProgressReporter) -> list[PhotoRead]:
            return photo_service.import_photos(paths, report_progress=report_progress)

        handle = self._jobs.submit("Importing photos", _job)
        self._pending_job_id = handle.id

    def _on_job_succeeded(self, job_id: str, result: object) -> None:
        if job_id != self._pending_job_id:
            return
        self._pending_job_id = None
        self.refresh()
        count = len(result) if isinstance(result, list) else 0
        self._notifications.post(
            f"Imported {count} photo{'s' if count != 1 else ''} into your library.",
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

    def _open_lightbox(self, photo: PhotoRead) -> None:
        index = next(i for i, item in enumerate(self._photos) if item.id == photo.id)
        dialog = LightboxDialog(
            self._photos, index, self._photo_service, self._notifications,
            on_changed=self.refresh, parent=self,
        )
        dialog.exec()

    def _delete(self, photo: PhotoRead) -> None:
        other_count = self._photo_service.count_relationships(photo.id)
        warning = (
            f" It is used in {other_count} place(s) and will be removed from all of them."
            if other_count
            else ""
        )
        if confirm_destructive_action(
            self,
            title="Delete Photo",
            message=f"Permanently delete this photo?{warning} This cannot be undone.",
            confirm_label="Delete Permanently",
        ):
            self._photo_service.delete_photo(photo.id)
            self.refresh()
