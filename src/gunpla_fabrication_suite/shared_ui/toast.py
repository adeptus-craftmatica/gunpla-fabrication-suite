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

_SEVERITY_GLYPH: dict[NotificationSeverity, str] = {
    NotificationSeverity.INFO: "ℹ",  # noqa: RUF001 - intentional info glyph
    NotificationSeverity.SUCCESS: "✓",
    NotificationSeverity.WARNING: "⚠",
    NotificationSeverity.ERROR: "✕",
}

_DISPLAY_DURATION_MS = 6000
_TOAST_WIDTH = 360


class _ToastCard(QFrame):
    def __init__(
        self, notification: Notification, on_dismiss: Callable[[_ToastCard], None]
    ) -> None:
        super().__init__()
        # Fix the width up front, before the layout's first sizeHint pass,
        # so the word-wrapped message label computes its wrapped height
        # against the width it will actually render at. Constraining the
        # width only *after* construction (e.g. via setMaximumWidth from the
        # caller) locks in a too-short height from the initial unconstrained
        # pass and clips the wrapped text top and bottom.
        self.setFixedWidth(_TOAST_WIDTH)
        self.setObjectName("toastCard")
        self.setProperty("severity", notification.severity.value)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 8, 8)

        symbol_label = QLabel(_SEVERITY_GLYPH[notification.severity])
        symbol_label.setObjectName("toastSymbol")
        symbol_label.setProperty("severity", notification.severity.value)
        symbol_label.setStyleSheet("font-weight: bold; border: none;")
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

        # Fix the height too, so ToastOverlay._stack (a QVBoxLayout, which
        # has weak height-for-width support through a nested layout) never
        # has to negotiate it and under-allocate. Deliberately uses
        # heightForWidth(_TOAST_WIDTH), NOT sizeHint().height(): plain
        # sizeHint() on this QFrame reflects the layout's *unconstrained*
        # preferred size — its reported width can come back wider than the
        # fixed width above, in which case its height is wrong too (the
        # word-wrapped label fits more text per notional line at that wider
        # width, under-counting how many lines it actually wraps to once
        # rendered at the true, narrower width) — for a short, single-line
        # message the two happen to agree, which is how this was missed
        # once already; only a longer, multi-line-wrapped message (e.g. a
        # full backup file path) exposes the gap.
        self.setFixedHeight(self.heightForWidth(_TOAST_WIDTH))


class ToastOverlay(QWidget):
    """A transparent overlay, sized to its parent, stacking toast cards bottom-right."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        # Click-through everywhere the overlay itself is empty — only the
        # toast cards (its children) should ever receive mouse events. This
        # widget covers the entire parent window (see _reposition), so
        # without this it silently swallows every click across the whole
        # shell, not just the corner where a toast happens to be.
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
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

    def reparent_to(self, new_parent: QWidget) -> None:
        """Move this overlay to sit on top of a different container.

        Needed when the shell rebuilds its central-widget arrangement (e.g.
        switching layouts) — this overlay isn't a normal child added via
        ``addWidget()``; it positions itself purely via an installed event
        filter keyed to whichever widget is currently its parent, so a plain
        ``setParent()`` alone would leave it watching the wrong (soon to be
        deleted) widget.
        """
        old_parent = self.parentWidget()
        if old_parent is not None:
            old_parent.removeEventFilter(self)
        self.setParent(new_parent)
        new_parent.installEventFilter(self)
        self._reposition()
        self.show()

    def _reposition(self) -> None:
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(0, 0, parent.width(), parent.height())
        self.raise_()

    def show_notification(self, notification: Notification) -> None:
        """Display ``notification`` as a card that auto-dismisses after a delay."""
        card = _ToastCard(notification, self._dismiss)
        self._stack.addWidget(card, alignment=Qt.AlignmentFlag.AlignRight)
        self.raise_()
        QTimer.singleShot(_DISPLAY_DURATION_MS, lambda: self._dismiss(card))

    def _dismiss(self, card: _ToastCard) -> None:
        self._stack.removeWidget(card)
        card.deleteLater()
