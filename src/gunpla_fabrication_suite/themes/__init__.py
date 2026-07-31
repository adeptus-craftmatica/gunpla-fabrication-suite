"""Shared visual theme system. Feature widgets must use PALETTE, never hardcoded colors."""

from __future__ import annotations

from gunpla_fabrication_suite.themes.amber import WORKSHOP_AMBER
from gunpla_fabrication_suite.themes.base import PALETTE, Theme, apply_theme, set_active_theme
from gunpla_fabrication_suite.themes.blueprint import BLUEPRINT
from gunpla_fabrication_suite.themes.dark import WORKSHOP_DARK
from gunpla_fabrication_suite.themes.neon_tokyo import NEON_TOKYO

THEMES: dict[str, Theme] = {
    theme.theme_id: theme for theme in (WORKSHOP_DARK, BLUEPRINT, WORKSHOP_AMBER, NEON_TOKYO)
}
DEFAULT_THEME = WORKSHOP_DARK

__all__ = [
    "BLUEPRINT",
    "DEFAULT_THEME",
    "NEON_TOKYO",
    "PALETTE",
    "THEMES",
    "WORKSHOP_AMBER",
    "WORKSHOP_DARK",
    "Theme",
    "apply_theme",
    "set_active_theme",
]
