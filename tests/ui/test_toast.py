"""Tests for toast notifications, including a regression test for a text-clipping bug.

Regression: constraining a toast card's width *after* constructing it (the
old code did ``card.setMaximumWidth(360)`` post-construction) locked in a
too-short height from the label's unconstrained first layout pass, clipping
wrapped text top and bottom. The fix fixes the width before the card's
layout ever runs.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from gunpla_fabrication_suite.core.notifications import NotificationCenter, NotificationSeverity
from gunpla_fabrication_suite.shared_ui.toast import _TOAST_WIDTH, ToastOverlay, _ToastCard
from gunpla_fabrication_suite.themes import WORKSHOP_DARK, apply_theme


def test_overlay_is_transparent_for_mouse_events(qtbot) -> None:
    """Regression: the overlay covers the entire shell window (see _reposition),
    so if it isn't click-through, it silently swallows every click across the
    whole app the moment it's constructed — not just clicks meant for a toast."""
    host = QWidget()
    qtbot.addWidget(host)
    host.show()

    overlay = ToastOverlay(host)

    assert overlay.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents) is True


def test_toast_card_width_is_fixed_before_layout_runs(qtbot) -> None:
    notification = NotificationCenter().post("Short message.")
    card = _ToastCard(notification, on_dismiss=lambda _card: None)
    qtbot.addWidget(card)

    assert card.width() == _TOAST_WIDTH


def test_long_message_toast_is_not_clipped(qtbot) -> None:
    """The card's fixed height must account for every wrapped line at its actual
    (fixed) width — never compressed below it. Deliberately checked against
    ``heightForWidth(_TOAST_WIDTH)``, not ``sizeHint()``: the latter reflects the
    layout's unconstrained preferred size, which can report a wider (and thus
    shorter, under-wrapped) size than the card's real fixed width."""
    long_message = (
        "This is an extremely long notification message designed specifically to "
        "force the toast card to wrap across several lines of text, to check that "
        "the reported height accounts for every wrapped line."
    )
    notification = NotificationCenter().post(long_message, severity=NotificationSeverity.WARNING)
    card = _ToastCard(notification, on_dismiss=lambda _card: None)
    qtbot.addWidget(card)
    card.show()

    assert card.height() == card.heightForWidth(_TOAST_WIDTH)
    assert card.height() > 40  # a single line would be much shorter than this


def test_overlay_shows_notification_at_full_height(qtbot, qapp) -> None:
    # The real app always applies its theme (which fixes font-size) before any
    # window exists — matching that here avoids font-metric timing quirks that
    # only occur with Qt's unthemed default fonts and don't reflect production.
    apply_theme(qapp, WORKSHOP_DARK)

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
    qtbot.waitUntil(lambda: card.height() == card.heightForWidth(_TOAST_WIDTH), timeout=1000)


def test_stacked_toast_height_is_correct_immediately_not_eventually(qtbot) -> None:
    """Regression: a card added to ToastOverlay's nested QVBoxLayout stack must get
    its full, correct height on the very first layout pass. QVBoxLayout's weak
    height-for-width support through a nested layout previously under-allocated
    height for a multi-line-wrapped message (e.g. a long backup file path),
    clipping the card's top and bottom — a bug the more lenient
    ``test_overlay_shows_notification_at_full_height`` (which tolerates up to a
    full second of eventual relayout via ``waitUntil``) didn't catch, since a
    real toast is only visible briefly and the user sees the clipped state
    before any deferred relayout could catch up.
    """
    host = QWidget()
    host.resize(500, 800)
    qtbot.addWidget(host)
    host.show()

    overlay = ToastOverlay(host)
    notifications = NotificationCenter()
    long_message = (
        "Backup saved to /Users/jonathanstrachan/Library/Application Support/"
        "GunplaFabricationSuite/backups/gunpla-backup-20260731T183000Z.zip."
    )
    overlay.show_notification(
        notifications.post(long_message, severity=NotificationSeverity.SUCCESS)
    )
    qtbot.wait(10)  # one deterministic tick — not the generous polling above

    card = overlay._stack.itemAt(0).widget()
    assert card is not None
    assert card.geometry().height() == card.heightForWidth(_TOAST_WIDTH)
