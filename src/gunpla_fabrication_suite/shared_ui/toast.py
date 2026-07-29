"""Non-blocking toast notifications anchored to a corner of a parent window.

Each toast communicates its severity through a symbol *and* text *and* a
border color — never color alone — so the distinction remains legible for
users with color-vision limitations.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from gunpla_fabrication_suite.core.notifications import Notification, NotificationSeverity
from gunpla_fabrication_suite.themes import PALETTE

_SEVERITY_STYLE: dict[NotificationSeverity, tuple[str, str]] = {
    NotificationSeverity.INFO: ("ℹ", PALETTE.accent),  # noqa: RUF001 - intentional info glyph
    NotificationSeverity.SUCCESS: ("✓", PALETTE.success),
    NotificationSeverity.WARNING: ("⚠", PALETTE.warning),
    NotificationSeverity.ERROR: ("✕", PALETTE.danger),
}

_DISPLAY_DURATION_MS = 6000


class _ToastCard(QFrame):
    def __init__(
        self, notification: Notification, on_dismiss: Callable[[_ToastCard], None]
    ) -> None:
        super().__init__()
        symbol, border_color = _SEVERITY_STYLE[notification.severity]
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {PALETTE.surface_raised};
                border: 1px solid {border_color};
                border-left: 4px solid {border_color};
                border-radius: 4px;
            }}
            """
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 8, 8)

        symbol_label = QLabel(symbol)
        symbol_label.setStyleSheet(f"color: {border_color}; font-weight: bold; border: none;")
        layout.addWidget(symbol_label)

        message_label = QLabel(notification.message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("border: none;")
        message_label.setAccessibleDescription(
            f"{notification.severity.value}: {notification.message}"
        )
        layout.addWidget(message_label, stretch=1)

        close_button = QPushButton("✕")
        close_button.setFixedSize(18, 18)
        close_button.setStyleSheet("border: none;")
        close_button.setToolTip("Dismiss")
        close_button.clicked.connect(lambda: on_dismiss(self))
        layout.addWidget(close_button)


class ToastOverlay(QWidget):
    """A transparent overlay, sized to its parent, stacking toast cards bottom-right."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 16, 16)
        outer.addStretch(1)

        self._stack = QVBoxLayout()
        self._stack.setSpacing(6)
        outer.addLayout(self._stack)
        outer.setAlignment(self._stack, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)

        parent.installEventFilter(self)
        self._reposition()
        self.show()

    def eventFilter(self, watched: object, event: QEvent) -> bool:
        if watched is self.parentWidget() and event.type() == QEvent.Type.Resize:
            self._reposition()
        return False

    def _reposition(self) -> None:
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(0, 0, parent.width(), parent.height())
        self.raise_()

    def show_notification(self, notification: Notification) -> None:
        """Display ``notification`` as a card that auto-dismisses after a delay."""
        card = _ToastCard(notification, self._dismiss)
        card.setMaximumWidth(360)
        self._stack.addWidget(card, alignment=Qt.AlignmentFlag.AlignRight)
        self.raise_()
        QTimer.singleShot(_DISPLAY_DURATION_MS, lambda: self._dismiss(card))

    def _dismiss(self, card: _ToastCard) -> None:
        self._stack.removeWidget(card)
        card.deleteLater()
