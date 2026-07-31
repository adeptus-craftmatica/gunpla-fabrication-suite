"""Blueprint: a light theme evoking actual engineering-drawing blueprints."""

from __future__ import annotations

from gunpla_fabrication_suite.themes.base import Theme

BLUEPRINT = Theme(
    theme_id="blueprint",
    name="Blueprint",
    is_dark=False,
    background="#eef1f7",
    surface="#ffffff",
    surface_raised="#e3e9f3",
    border="#c7d2e3",
    text_primary="#1b2a41",
    text_secondary="#54637a",
    text_disabled="#a3aec0",
    accent="#1e5fae",
    accent_hover="#2f74c9",
    success="#2f9e5b",
    warning="#b7791f",
    danger="#c0392b",
    focus_ring="#2f74c9",
)
