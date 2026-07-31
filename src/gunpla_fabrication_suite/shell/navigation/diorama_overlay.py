"""The Diorama layout's navigation: an edge-hover auto-hide overlay.

Unlike Rail/Command Deck/Workbench's nav widgets, which occupy permanent
layout space, this floats on top of the workspace — like `ToastOverlay` —
collapsed to a thin edge strip so content runs full-bleed, and only
expands to show `NavigationRail`'s buttons while the cursor is near it.
"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QEnterEvent
from PySide6.QtWidgets import QWidget

from gunpla_fabrication_suite.shell.navigation.rail import NavigationRail

_COLLAPSED_WIDTH = 10
_EXPANDED_WIDTH = 220
_EDGE_INDICATOR_WIDTH = 3
_COLLAPSE_DELAY_MS = 300
_ANIMATION_MS = 150


class DioramaNavOverlay(QWidget):
    """A collapsed edge strip that expands into `NavigationRail` on hover.

    Children are positioned manually (no layout) — `NavigationRail` always
    spans this overlay's full current width, and a thin accent-colored
    strip is pinned to the trailing edge on top of it. Without that
    explicit top layer, the rail's own opaque background would paint over
    whatever hint marks this edge as hoverable, since it's an opaque child
    covering the exact same clipped region.

    Every widget positioned this way (via `setGeometry()`, not a `QLayout`)
    needs `WA_StyledBackground` set explicitly — a plain `QWidget` only
    paints its QSS `background-color`/`border` automatically when a layout
    manages it (as `NavigationRail` normally is, inside Rail's splitter);
    manually positioning it elsewhere leaves it fully transparent.
    """

    def __init__(self, nav_rail: NavigationRail, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("dioramaNavOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMouseTracking(True)

        self._nav_rail = nav_rail
        nav_rail.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        nav_rail.setMouseTracking(True)

        self._edge_indicator = QWidget(self)
        self._edge_indicator.setObjectName("dioramaEdgeIndicator")
        self._edge_indicator.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._edge_indicator.setMouseTracking(True)

        self._collapse_timer = QTimer(self)
        self._collapse_timer.setSingleShot(True)
        self._collapse_timer.timeout.connect(self._collapse)

        self._animation = QVariantAnimation(self)
        self._animation.setDuration(_ANIMATION_MS)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.valueChanged.connect(self._on_width_changed)

        parent.installEventFilter(self)
        self.resize(_COLLAPSED_WIDTH, parent.height())
        self.attach_nav_rail()
        self.raise_()
        self.show()

    def attach_nav_rail(self) -> None:
        """(Re-)claim the shared `NavigationRail` instance as this overlay's child.

        The shell detaches ``nav_rail`` from whatever currently owns it
        (``setParent(None)``) at the top of every layout switch, including
        switches *back into* Diorama — that unconditional detach is what
        lets the other three layouts reuse it safely, but it also strips
        it out of this overlay each time, even when Diorama is reactivated
        with an already-existing overlay. Call this every time Diorama
        becomes the active layout, not just on first construction, or the
        expanded overlay renders with nothing in it.
        """
        self._nav_rail.setParent(self)
        self._nav_rail.show()
        self._layout_children()

    def enterEvent(self, event: QEnterEvent) -> None:
        self._collapse_timer.stop()
        self._animate_to(_EXPANDED_WIDTH)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._collapse_timer.start(_COLLAPSE_DELAY_MS)
        super().leaveEvent(event)

    def eventFilter(self, watched: object, event: QEvent) -> bool:
        if watched is self.parentWidget() and event.type() == QEvent.Type.Resize:
            self._reposition()
        return False

    def reparent_to(self, new_parent: QWidget) -> None:
        """Move this overlay to sit on top of a different container.

        Mirrors `ToastOverlay.reparent_to` — this overlay isn't a normal
        child added via `addWidget()`; it positions itself purely via an
        installed event filter keyed to whichever widget is currently its
        parent, so a plain `setParent()` alone would leave it watching the
        wrong (soon to be deleted) widget.
        """
        self._collapse_timer.stop()
        self._animation.stop()
        self.resize(_COLLAPSED_WIDTH, self.height())

        old_parent = self.parentWidget()
        if old_parent is not None:
            old_parent.removeEventFilter(self)
        self.setParent(new_parent)
        new_parent.installEventFilter(self)
        self._reposition()
        self.show()

    def _collapse(self) -> None:
        self._animate_to(_COLLAPSED_WIDTH)

    def _animate_to(self, target: int) -> None:
        self._animation.stop()
        self._animation.setStartValue(self.width())
        self._animation.setEndValue(target)
        self._animation.start()

    def _on_width_changed(self, value: int) -> None:
        self.resize(value, self.height())
        self._layout_children()

    def _reposition(self) -> None:
        parent = self.parentWidget()
        if parent is not None:
            self.resize(self.width(), parent.height())
        self._layout_children()
        self.raise_()

    def _layout_children(self) -> None:
        self._nav_rail.setGeometry(0, 0, self.width(), self.height())
        self._edge_indicator.setGeometry(
            max(self.width() - _EDGE_INDICATOR_WIDTH, 0), 0, _EDGE_INDICATOR_WIDTH, self.height()
        )
        self._edge_indicator.raise_()
