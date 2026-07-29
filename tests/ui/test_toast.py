"""Tests for toast notifications, including a regression test for a text-clipping bug.

Regression: constraining a toast card's width *after* constructing it (the
old code did ``card.setMaximumWidth(360)`` post-construction) locked in a
too-short height from the label's unconstrained first layout pass, clipping
wrapped text top and bottom. The fix fixes the width before the card's
layout ever runs.
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from gunpla_fabrication_suite.core.notifications import NotificationCenter, NotificationSeverity
from gunpla_fabrication_suite.shared_ui.toast import _TOAST_WIDTH, ToastOverlay, _ToastCard
from gunpla_fabrication_suite.themes import apply_dark_theme


def test_toast_card_width_is_fixed_before_layout_runs(qtbot) -> None:
    notification = NotificationCenter().post("Short message.")
    card = _ToastCard(notification, on_dismiss=lambda _card: None)
    qtbot.addWidget(card)

    assert card.width() == _TOAST_WIDTH


def test_long_message_toast_is_not_clipped(qtbot) -> None:
    """The card's actual height must match its sizeHint — never compressed below it."""
    long_message = (
        "This is an extremely long notification message designed specifically to "
        "force the toast card to wrap across several lines of text, to check that "
        "the reported height accounts for every wrapped line."
    )
    notification = NotificationCenter().post(long_message, severity=NotificationSeverity.WARNING)
    card = _ToastCard(notification, on_dismiss=lambda _card: None)
    qtbot.addWidget(card)
    card.show()

    # A tall, roomy host ensures nothing external compresses the card, isolating
    # whether the card's *own* layout computed a correct (non-clipped) height.
    card.resize(card.sizeHint())

    assert card.height() == card.sizeHint().height()
    assert card.height() > 40  # a single line would be much shorter than this


def test_overlay_shows_notification_at_full_height(qtbot, qapp) -> None:
    # The real app always applies its theme (which fixes font-size) before any
    # window exists — matching that here avoids font-metric timing quirks that
    # only occur with Qt's unthemed default fonts and don't reflect production.
    apply_dark_theme(qapp)

    host = QWidget()
    host.resize(500, 800)
    qtbot.addWidget(host)
    host.show()

    overlay = ToastOverlay(host)
    notifications = NotificationCenter()
    overlay.show_notification(
        notifications.post(
            "Plugin 'Build Planner' failed to load: Build Planner requires the Kit "
            "Library plugin's KitService, which was not found in the service container.",
            severity=NotificationSeverity.WARNING,
        )
    )

    card = overlay._stack.itemAt(0).widget()
    assert card is not None
    qtbot.waitUntil(lambda: card.height() == card.sizeHint().height(), timeout=1000)
