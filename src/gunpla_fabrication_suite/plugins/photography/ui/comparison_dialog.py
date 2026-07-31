"""A before/after progress-photo comparison with a draggable reveal slider."""

from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPen, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from gunpla_fabrication_suite.plugins.photography.schemas import PhotoRead
from gunpla_fabrication_suite.plugins.photography.services.photo_service import PhotoService
from gunpla_fabrication_suite.themes import PALETTE

_DIVIDER_WIDTH = 2


class _ComparisonCanvas(QWidget):
    """Paints two images, revealing ``before`` from the left up to a split fraction."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._before = QPixmap()
        self._after = QPixmap()
        self._split = 0.5
        self.setMinimumSize(320, 240)

    def set_pixmaps(self, before: QPixmap, after: QPixmap) -> None:
        self._before = before
        self._after = after
        self.update()

    def set_split(self, fraction: float) -> None:
        self._split = max(0.0, min(1.0, fraction))
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        target = self.rect()
        painter = QPainter(self)
        painter.fillRect(target, QColor(PALETTE.surface))

        if self._after.isNull() or self._before.isNull():
            painter.end()
            return

        after_crop = self._cover_crop(self._after, target.size())
        before_crop = self._cover_crop(self._before, target.size())

        painter.drawPixmap(0, 0, after_crop)
        split_x = int(target.width() * self._split)
        painter.drawPixmap(0, 0, before_crop, 0, 0, split_x, before_crop.height())

        painter.setPen(QPen(QColor(PALETTE.accent), _DIVIDER_WIDTH))
        painter.drawLine(split_x, 0, split_x, target.height())
        painter.end()

    @staticmethod
    def _cover_crop(pixmap: QPixmap, size: QSize) -> QPixmap:
        """Scale ``pixmap`` to fully cover ``size``, then center-crop to it exactly."""
        scaled = pixmap.scaled(
            size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = max(0, (scaled.width() - size.width()) // 2)
        y = max(0, (scaled.height() - size.height()) // 2)
        return scaled.copy(QRect(x, y, size.width(), size.height()))


class ComparisonDialog(QDialog):
    """Lets the user pick two photos from a gallery and slide between them."""

    def __init__(
        self,
        photos: list[PhotoRead],
        photo_service: PhotoService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Before / After Comparison")
        self.resize(820, 640)

        self._photo_service = photo_service
        self._photos = sorted(photos, key=lambda photo: photo.created_at)

        outer = QVBoxLayout(self)

        picker_row = QHBoxLayout()
        picker_row.addWidget(QLabel("Before:"))
        self._before_combo = QComboBox()
        picker_row.addWidget(self._before_combo, stretch=1)
        picker_row.addWidget(QLabel("After:"))
        self._after_combo = QComboBox()
        picker_row.addWidget(self._after_combo, stretch=1)
        outer.addLayout(picker_row)

        for combo in (self._before_combo, self._after_combo):
            for photo in self._photos:
                label = photo.caption or photo.created_at.strftime("%b %d, %Y  %H:%M")
                combo.addItem(label, photo)

        self._canvas = _ComparisonCanvas()
        outer.addWidget(self._canvas, stretch=1)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 100)
        self._slider.setValue(50)
        self._slider.valueChanged.connect(lambda value: self._canvas.set_split(value / 100))
        outer.addWidget(self._slider)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        outer.addWidget(button_box)

        if len(self._photos) >= 2:
            self._before_combo.setCurrentIndex(0)
            self._after_combo.setCurrentIndex(len(self._photos) - 1)
        self._before_combo.currentIndexChanged.connect(self._reload_images)
        self._after_combo.currentIndexChanged.connect(self._reload_images)
        self._reload_images()

    def _reload_images(self) -> None:
        before: PhotoRead | None = self._before_combo.currentData()
        after: PhotoRead | None = self._after_combo.currentData()
        if before is None or after is None:
            return
        self._canvas.set_pixmaps(
            QPixmap(str(self._photo_service.resolve_preview_path(before))),
            QPixmap(str(self._photo_service.resolve_preview_path(after))),
        )
