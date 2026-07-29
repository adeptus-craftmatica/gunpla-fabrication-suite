"""Tests for EmptyStateWidget, including a regression test for a text-clipping bug.

Regression: the description label's wrapped height was computed by Qt's own
QLabel word-wrap layout machinery, which turned out not to reliably converge
once nested inside a QScrollArea (as it is inside the Build Planner's
journal panel) — it could settle on a height shorter than the wrapped text
needed and never self-correct, clipping the last line top and bottom. The
fix computes the exact wrapped height with QFontMetrics instead of relying
on QLabel/layout convergence.
"""

from __future__ import annotations

from PySide6.QtWidgets import QScrollArea

from gunpla_fabrication_suite.shared_ui.empty_state import (
    _DESCRIPTION_MAX_WIDTH,
    _DESCRIPTION_MIN_WIDTH,
    EmptyStateWidget,
)

_LONG_DESCRIPTION = "Log what you did right after a session, while it's fresh."


def test_widget_without_description_has_no_description_label(qtbot) -> None:
    widget = EmptyStateWidget(title="Nothing here")
    qtbot.addWidget(widget)

    assert widget._description_label is None


def test_description_label_height_covers_all_wrapped_lines(qtbot) -> None:
    """At a narrow width the description wraps to 2+ lines; height must fit all of them."""
    widget = EmptyStateWidget(title="No journal entries yet", description=_LONG_DESCRIPTION)
    qtbot.addWidget(widget)
    widget.resize(260, 300)
    widget.show()

    label = widget._description_label
    assert label is not None

    from PySide6.QtCore import QRect, Qt
    from PySide6.QtGui import QFontMetrics

    metrics = QFontMetrics(label.font())
    expected = metrics.boundingRect(
        QRect(0, 0, label.width(), 0), int(Qt.TextFlag.TextWordWrap), label.text()
    )
    # The label's fixed height must be at least the true wrapped-text height —
    # never shorter (that's the clip) — matching within a small buffer.
    assert label.height() >= expected.height()


def test_description_label_never_exceeds_max_width(qtbot) -> None:
    widget = EmptyStateWidget(title="Title", description=_LONG_DESCRIPTION)
    qtbot.addWidget(widget)
    widget.resize(2000, 300)
    widget.show()

    assert widget._description_label.width() <= _DESCRIPTION_MAX_WIDTH


def test_description_label_never_narrower_than_minimum(qtbot) -> None:
    widget = EmptyStateWidget(title="Title", description=_LONG_DESCRIPTION)
    qtbot.addWidget(widget)
    widget.resize(50, 300)
    widget.show()

    assert widget._description_label.width() >= _DESCRIPTION_MIN_WIDTH


def test_journal_empty_state_is_not_clipped_inside_a_scroll_area(qtbot, journal_service) -> None:
    """The exact reported bug: EmptyStateWidget nested inside build_detail_view's QScrollArea."""
    from gunpla_fabrication_suite.plugins.build_planner.ui.journal_widget import JournalWidget

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    qtbot.addWidget(scroll)
    scroll.resize(350, 400)

    widget = JournalWidget(journal_service, "fake-build-id")
    scroll.setWidget(widget)
    scroll.show()

    empty_state = widget._feed_layout.itemAt(0).widget()
    assert isinstance(empty_state, EmptyStateWidget)
    label = empty_state._description_label
    assert label is not None

    from PySide6.QtCore import QRect, Qt
    from PySide6.QtGui import QFontMetrics

    metrics = QFontMetrics(label.font())
    expected = metrics.boundingRect(
        QRect(0, 0, label.width(), 0), int(Qt.TextFlag.TextWordWrap), label.text()
    )
    assert label.height() >= expected.height()
