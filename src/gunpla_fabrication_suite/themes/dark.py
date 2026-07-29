"""The default dark, neutral-grayscale theme.

Feature widgets should reference :class:`DarkPalette` (or a future
``LightPalette``/``HighContrastPalette``) instead of hardcoding hex colors,
so a future theme switch or accessibility mode only has to change this
module.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


@dataclass(frozen=True, slots=True)
class DarkPalette:
    """Named colors for the dark theme. Never reference raw hex codes in widgets."""

    background: str = "#1e1f22"
    surface: str = "#26282c"
    surface_raised: str = "#2f3136"
    border: str = "#3c3f44"
    text_primary: str = "#e8e9ec"
    text_secondary: str = "#a6a9b0"
    text_disabled: str = "#6c6f75"
    accent: str = "#5b8def"
    accent_hover: str = "#7aa2f2"
    success: str = "#4caf7d"
    warning: str = "#d9a441"
    danger: str = "#d9534f"
    focus_ring: str = "#7aa2f2"


PALETTE = DarkPalette()

_STYLESHEET = f"""
QWidget {{
    color: {PALETTE.text_primary};
    font-size: 13px;
}}
QMainWindow, QDialog {{
    background-color: {PALETTE.background};
}}
QToolTip {{
    background-color: {PALETTE.surface_raised};
    color: {PALETTE.text_primary};
    border: 1px solid {PALETTE.border};
    padding: 4px 8px;
}}
QMenuBar, QMenu {{
    background-color: {PALETTE.surface};
    color: {PALETTE.text_primary};
}}
QMenu::item:selected {{
    background-color: {PALETTE.accent};
}}
QStatusBar {{
    background-color: {PALETTE.surface};
    border-top: 1px solid {PALETTE.border};
}}
QPushButton {{
    background-color: {PALETTE.surface_raised};
    border: 1px solid {PALETTE.border};
    border-radius: 4px;
    padding: 6px 14px;
}}
QPushButton:hover {{
    border-color: {PALETTE.accent};
}}
QPushButton:pressed {{
    background-color: {PALETTE.border};
}}
QPushButton:default {{
    background-color: {PALETTE.accent};
    border-color: {PALETTE.accent};
    color: white;
}}
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDateEdit {{
    background-color: {PALETTE.surface};
    border: 1px solid {PALETTE.border};
    border-radius: 4px;
    padding: 4px 6px;
    selection-background-color: {PALETTE.accent};
}}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
    border: 1px solid {PALETTE.focus_ring};
}}
QTableView, QTreeView, QListView {{
    background-color: {PALETTE.surface};
    alternate-background-color: {PALETTE.surface_raised};
    border: 1px solid {PALETTE.border};
    gridline-color: {PALETTE.border};
}}
QHeaderView::section {{
    background-color: {PALETTE.surface_raised};
    border: none;
    border-bottom: 1px solid {PALETTE.border};
    padding: 6px;
}}
QSplitter::handle {{
    background-color: {PALETTE.border};
}}
QTabBar::tab {{
    background-color: {PALETTE.surface};
    padding: 6px 12px;
    border: 1px solid {PALETTE.border};
    border-bottom: none;
}}
QTabBar::tab:selected {{
    background-color: {PALETTE.surface_raised};
    border-bottom: 2px solid {PALETTE.accent};
}}
QScrollBar:vertical, QScrollBar:horizontal {{
    background: {PALETTE.background};
}}
QScrollBar::handle {{
    background: {PALETTE.border};
    border-radius: 4px;
}}
*:focus {{
    outline: none;
}}
"""


def apply_dark_theme(app: QApplication) -> None:
    """Apply the dark palette and stylesheet to the whole application."""
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(PALETTE.background))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(PALETTE.text_primary))
    palette.setColor(QPalette.ColorRole.Base, QColor(PALETTE.surface))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(PALETTE.surface_raised))
    palette.setColor(QPalette.ColorRole.Text, QColor(PALETTE.text_primary))
    palette.setColor(QPalette.ColorRole.Button, QColor(PALETTE.surface_raised))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(PALETTE.text_primary))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(PALETTE.accent))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("white"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(PALETTE.surface_raised))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(PALETTE.text_primary))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(PALETTE.text_secondary))
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(PALETTE.text_disabled)
    )

    app.setStyle("Fusion")
    app.setPalette(palette)
    app.setStyleSheet(_STYLESHEET)
