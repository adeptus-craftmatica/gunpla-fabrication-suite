"""Visual importance ("kind") for QPushButton, via Qt's dynamic-property QSS selectors."""

from __future__ import annotations

from typing import Literal

from PySide6.QtWidgets import QPushButton

ButtonKind = Literal["primary", "secondary", "ghost", "danger", "nav"]


def set_button_kind(button: QPushButton, kind: ButtonKind) -> None:
    """Mark a button's visual importance so the shared stylesheet renders it consistently.

    Establishes a real hierarchy — primary (accent-filled), secondary (the
    neutral default), ghost (flat, borderless), danger (destructive), nav
    (the navigation rail's own selection state) — instead of every button
    on a page looking identically neutral regardless of what it does. The
    actual look for each kind lives in exactly one place: the
    ``QPushButton[kind="..."]`` rules in ``themes/base.py``, not in a
    per-widget inline stylesheet.
    """
    button.setProperty("kind", kind)
    # Only strictly needed if `kind` changes after the button was already
    # polished with a different value — cheap defensive call regardless,
    # so nobody has to rediscover this footgun for a later runtime change.
    button.style().unpolish(button)
    button.style().polish(button)
