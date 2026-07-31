"""Visual role for QLabel, via Qt's dynamic-property QSS selectors.

Same idiom as ``shared_ui/buttons.py``'s button "kind": the actual look for
each role lives in exactly one place — the ``QLabel[role="..."]`` rules in
``themes/base.py``'s ``build_stylesheet()`` — instead of being baked into a
one-shot ``setStyleSheet(f"...{PALETTE.x}...")`` call that would go stale
the moment the active theme changes.
"""

from __future__ import annotations

from typing import Literal

from PySide6.QtWidgets import QLabel

LabelRole = Literal["section-title", "secondary", "caption"]


def set_label_role(label: QLabel, role: LabelRole) -> None:
    """Mark a label's visual role so the shared stylesheet renders it consistently."""
    label.setProperty("role", role)
    label.style().unpolish(label)
    label.style().polish(label)
