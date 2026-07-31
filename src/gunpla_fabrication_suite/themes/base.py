"""The theme mechanism: a `Theme` data shape, a live-reactive `PALETTE` proxy,
and the machinery to apply a theme to a running `QApplication`.

Widgets should reference :data:`PALETTE` (never raw hex colors) so a theme
switch reaches every widget without per-file changes.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


@dataclass(frozen=True, slots=True)
class Theme:
    """Named colors and identity for one selectable theme.

    Never reference raw hex codes in widgets — go through :data:`PALETTE`.
    """

    theme_id: str
    name: str
    is_dark: bool
    background: str
    surface: str
    surface_raised: str
    border: str
    text_primary: str
    text_secondary: str
    text_disabled: str
    accent: str
    accent_hover: str
    success: str
    warning: str
    danger: str
    focus_ring: str


# Defined here (not in dark.py) specifically so `_active` always has a real
# value from the moment this module is first imported — module-level code
# elsewhere (e.g. shared_ui/tokens.py's color-bearing constants) reads
# PALETTE.* at *their own* import time, which happens before anything in
# application/bootstrap.py has had a chance to call apply_theme(). dark.py
# re-exports this same instance, so there is exactly one Workshop Dark.
WORKSHOP_DARK = Theme(
    theme_id="workshop_dark",
    name="Workshop Dark",
    is_dark=True,
    background="#1e1f22",
    surface="#26282c",
    surface_raised="#2f3136",
    border="#3c3f44",
    text_primary="#e8e9ec",
    text_secondary="#a6a9b0",
    text_disabled="#6c6f75",
    accent="#5b8def",
    accent_hover="#7aa2f2",
    success="#4caf7d",
    warning="#d9a441",
    danger="#d9534f",
    focus_ring="#7aa2f2",
)

_active: Theme = WORKSHOP_DARK


class _PaletteProxy:
    """Forwards attribute access to whichever `Theme` is currently active.

    Kept as exactly one object, never replaced, so every existing
    ``from gunpla_fabrication_suite.themes import PALETTE`` binding stays
    valid across a live theme switch — only which `Theme` it forwards to
    changes, never the proxy object itself. Anything needing real
    dataclass introspection (iterating fields, `dataclasses.asdict`, ...)
    must go through :attr:`ThemeManager.current` instead of this proxy.
    """

    def __getattr__(self, name: str) -> str | bool:
        field_names = {f.name for f in dataclasses.fields(_active)}
        if name not in field_names:
            raise AttributeError(f"Theme has no field {name!r}")
        return cast("str | bool", getattr(_active, name))


if TYPE_CHECKING:
    # Lets mypy check PALETTE.<field> against Theme's real per-field types,
    # instead of the proxy's __getattr__ collapsing everything to Any.
    PALETTE: Theme
else:
    PALETTE = _PaletteProxy()


def set_active_theme(theme: Theme) -> None:
    """Point :data:`PALETTE` at ``theme``. Does not touch the QApplication — see `apply_theme`."""
    global _active
    _active = theme


def build_stylesheet(theme: Theme) -> str:
    """Build the app-wide Qt stylesheet for ``theme``.

    Rebuilt fresh from ``theme`` every call — never cached — so switching
    themes always produces a stylesheet with that theme's own colors, not
    whichever theme happened to be active when a module was first imported.
    """
    return f"""
QWidget {{
    color: {theme.text_primary};
    font-size: 13px;
}}
QMainWindow, QDialog {{
    background-color: {theme.background};
}}
QToolTip {{
    background-color: {theme.surface_raised};
    color: {theme.text_primary};
    border: 1px solid {theme.border};
    padding: 4px 8px;
}}
QMenuBar, QMenu {{
    background-color: {theme.surface};
    color: {theme.text_primary};
}}
QMenu::item:selected {{
    background-color: {theme.accent};
}}
QStatusBar {{
    background-color: {theme.surface};
    border-top: 1px solid {theme.border};
}}
QPushButton {{
    background-color: {theme.surface_raised};
    border: 1px solid {theme.border};
    border-radius: 4px;
    padding: 6px 14px;
}}
QPushButton:hover {{
    border-color: {theme.accent};
}}
QPushButton:pressed {{
    background-color: {theme.border};
}}
QPushButton:default {{
    background-color: {theme.accent};
    border-color: {theme.accent};
    color: white;
}}
QPushButton[kind="primary"] {{
    background-color: {theme.accent};
    border-color: {theme.accent};
    color: white;
}}
QPushButton[kind="primary"]:hover {{
    background-color: {theme.accent_hover};
    border-color: {theme.accent_hover};
}}
QPushButton[kind="primary"]:disabled {{
    background-color: {theme.surface_raised};
    border-color: {theme.border};
    color: {theme.text_disabled};
}}
QPushButton[kind="ghost"] {{
    background-color: transparent;
    border: 1px solid transparent;
}}
QPushButton[kind="ghost"]:hover {{
    background-color: {theme.surface_raised};
}}
QPushButton[kind="danger"] {{
    color: {theme.danger};
    border-color: {theme.danger};
}}
QPushButton[kind="danger"]:hover {{
    background-color: {theme.danger};
    color: white;
}}
QPushButton[kind="danger"]:disabled {{
    color: {theme.text_disabled};
    border-color: {theme.border};
}}
QPushButton[kind="nav"] {{
    text-align: left;
    padding: 10px 14px;
    border: none;
    border-radius: 6px;
    font-weight: 500;
}}
QPushButton[kind="nav"]:checked {{
    background-color: {theme.accent};
    color: white;
    font-weight: 600;
}}
QPushButton[kind="nav"]:hover:!checked {{
    background-color: {theme.surface_raised};
}}
QPushButton[kind="nav"]#compactRailButton {{
    text-align: center;
    padding: 8px 2px;
}}
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDateEdit {{
    background-color: {theme.surface};
    border: 1px solid {theme.border};
    border-radius: 4px;
    padding: 4px 6px;
    selection-background-color: {theme.accent};
}}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
    border: 1px solid {theme.focus_ring};
}}
QTableView, QTreeView, QListView {{
    background-color: {theme.surface};
    alternate-background-color: {theme.surface_raised};
    border: 1px solid {theme.border};
    gridline-color: {theme.border};
}}
QHeaderView::section {{
    background-color: {theme.surface_raised};
    border: none;
    border-bottom: 1px solid {theme.border};
    padding: 6px;
}}
QSplitter::handle {{
    background-color: {theme.border};
}}
QSplitter::handle:hover {{
    background-color: {theme.accent};
}}
QTabBar::tab {{
    background-color: {theme.surface};
    padding: 6px 12px;
    border: 1px solid {theme.border};
    border-bottom: none;
}}
QTabBar::tab:selected {{
    background-color: {theme.surface_raised};
    border-bottom: 2px solid {theme.accent};
}}
QScrollBar:vertical, QScrollBar:horizontal {{
    background: {theme.background};
}}
QScrollBar::handle {{
    background: {theme.border};
    border-radius: 4px;
}}
#card {{
    background-color: {theme.surface};
    border: 1px solid {theme.border};
    border-radius: 8px;
}}
#inspectorPanel {{
    background-color: {theme.surface};
    border-left: 1px solid {theme.border};
}}
#navigationRail {{
    background-color: {theme.surface};
    border-right: 1px solid {theme.border};
}}
#topNavBar {{
    background-color: {theme.surface};
    border-bottom: 1px solid {theme.border};
}}
#compactRail {{
    background-color: {theme.surface};
    border-right: 1px solid {theme.border};
}}
#dioramaNavOverlay {{
    background-color: {theme.surface};
}}
#dioramaEdgeIndicator {{
    background-color: {theme.accent};
}}
#toastCard[severity="info"] {{
    background-color: {theme.surface_raised};
    border: 1px solid {theme.accent};
    border-left: 4px solid {theme.accent};
    border-radius: 4px;
}}
#toastCard[severity="success"] {{
    background-color: {theme.surface_raised};
    border: 1px solid {theme.success};
    border-left: 4px solid {theme.success};
    border-radius: 4px;
}}
#toastCard[severity="warning"] {{
    background-color: {theme.surface_raised};
    border: 1px solid {theme.warning};
    border-left: 4px solid {theme.warning};
    border-radius: 4px;
}}
#toastCard[severity="error"] {{
    background-color: {theme.surface_raised};
    border: 1px solid {theme.danger};
    border-left: 4px solid {theme.danger};
    border-radius: 4px;
}}
#toastSymbol[severity="info"] {{
    color: {theme.accent};
}}
#toastSymbol[severity="success"] {{
    color: {theme.success};
}}
#toastSymbol[severity="warning"] {{
    color: {theme.warning};
}}
#toastSymbol[severity="error"] {{
    color: {theme.danger};
}}
#kanbanColumn {{
    background-color: {theme.surface};
    border: 1px solid {theme.border};
    border-radius: 6px;
}}
#kanbanCard {{
    text-align: left;
    padding: 8px;
    background-color: {theme.surface_raised};
    border: 1px solid {theme.border};
    border-radius: 4px;
}}
QLabel[role="section-title"] {{
    font-size: 13px;
    font-weight: 600;
    color: {theme.text_secondary};
    border: none;
}}
QLabel[role="secondary"] {{
    color: {theme.text_secondary};
}}
QLabel[role="caption"] {{
    font-size: 11px;
    color: {theme.text_secondary};
}}
#photoThumbnailImage {{
    background-color: {theme.surface};
    border: 1px solid {theme.border};
    border-radius: 4px;
}}
#photoThumbnailImage[hero="true"] {{
    border-color: {theme.accent};
}}
#statusSegment {{
    color: {theme.text_secondary};
    padding: 0 10px;
}}
#statusSegment[status="ok"] {{
    color: {theme.success};
}}
#statusSegment[status="warning"] {{
    color: {theme.warning};
}}
#statusSegment[status="error"] {{
    color: {theme.danger};
}}
#journalEntry {{
    padding: 8px;
    background-color: {theme.surface};
    border: 1px solid {theme.border};
    border-radius: 4px;
}}
*:focus {{
    outline: none;
}}
"""


def apply_theme(app: QApplication, theme: Theme) -> None:
    """Apply ``theme``'s palette and stylesheet to the whole application, live.

    Safe to call more than once on an already-running app: rebuilds the
    QPalette and stylesheet fresh, then explicitly unpolishes/repolishes
    every existing widget, since Qt does not document that a full
    stylesheet swap alone cascades to every already-visible descendant.
    """
    set_active_theme(theme)

    qpalette = QPalette()
    qpalette.setColor(QPalette.ColorRole.Window, QColor(theme.background))
    qpalette.setColor(QPalette.ColorRole.WindowText, QColor(theme.text_primary))
    qpalette.setColor(QPalette.ColorRole.Base, QColor(theme.surface))
    qpalette.setColor(QPalette.ColorRole.AlternateBase, QColor(theme.surface_raised))
    qpalette.setColor(QPalette.ColorRole.Text, QColor(theme.text_primary))
    qpalette.setColor(QPalette.ColorRole.Button, QColor(theme.surface_raised))
    qpalette.setColor(QPalette.ColorRole.ButtonText, QColor(theme.text_primary))
    qpalette.setColor(QPalette.ColorRole.Highlight, QColor(theme.accent))
    qpalette.setColor(QPalette.ColorRole.HighlightedText, QColor("white"))
    qpalette.setColor(QPalette.ColorRole.ToolTipBase, QColor(theme.surface_raised))
    qpalette.setColor(QPalette.ColorRole.ToolTipText, QColor(theme.text_primary))
    qpalette.setColor(QPalette.ColorRole.PlaceholderText, QColor(theme.text_secondary))
    qpalette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(theme.text_disabled)
    )

    app.setStyle("Fusion")
    app.setPalette(qpalette)
    app.setStyleSheet(build_stylesheet(theme))

    for widget in app.allWidgets():
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()
