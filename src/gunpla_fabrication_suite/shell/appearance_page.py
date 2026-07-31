"""The Appearance settings page: pick a theme and a layout, both live."""

from __future__ import annotations

from PySide6.QtWidgets import QButtonGroup, QRadioButton, QVBoxLayout, QWidget

from gunpla_fabrication_suite.core.layout import LayoutManager
from gunpla_fabrication_suite.core.theming import ThemeManager
from gunpla_fabrication_suite.shared_ui import Card, PageHeader


class AppearancePage(QWidget):
    """Lets the user switch themes and layouts — both apply immediately, no restart."""

    def __init__(
        self,
        theme_manager: ThemeManager,
        layout_manager: LayoutManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._theme_manager = theme_manager
        self._layout_manager = layout_manager

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(16)

        outer.addWidget(
            PageHeader(
                "Appearance",
                subtitle="Themes and layouts apply immediately — no restart needed.",
            )
        )

        theme_card = Card("Theme")
        theme_group = QButtonGroup(self)
        theme_group.setExclusive(True)
        for theme in theme_manager.available_themes():
            button = QRadioButton(theme.name)
            button.setChecked(theme.theme_id == theme_manager.current.theme_id)
            button.toggled.connect(
                lambda checked, theme_id=theme.theme_id: self._on_theme_toggled(checked, theme_id)
            )
            theme_group.addButton(button)
            theme_card.add_widget(button)
        self._theme_group = theme_group
        outer.addWidget(theme_card)

        layout_card = Card("Layout")
        layout_group = QButtonGroup(self)
        layout_group.setExclusive(True)
        for layout_id, display_name in layout_manager.available_layouts():
            button = QRadioButton(display_name)
            button.setChecked(layout_id == layout_manager.current)
            button.toggled.connect(
                lambda checked, layout_id=layout_id: self._on_layout_toggled(checked, layout_id)
            )
            layout_group.addButton(button)
            layout_card.add_widget(button)
        self._layout_group = layout_group
        outer.addWidget(layout_card)

        outer.addStretch(1)

    def _on_theme_toggled(self, checked: bool, theme_id: str) -> None:
        if checked:
            self._theme_manager.set_theme(theme_id)

    def _on_layout_toggled(self, checked: bool, layout_id: str) -> None:
        if checked:
            self._layout_manager.set_layout(layout_id)
