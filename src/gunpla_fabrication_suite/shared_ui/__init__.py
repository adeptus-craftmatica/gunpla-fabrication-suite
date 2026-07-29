"""Reusable, theme-aware widgets and dialogs shared across the shell and plugins."""

from __future__ import annotations

from gunpla_fabrication_suite.shared_ui.confirm_dialog import confirm_destructive_action
from gunpla_fabrication_suite.shared_ui.empty_state import EmptyStateWidget
from gunpla_fabrication_suite.shared_ui.toast import ToastOverlay

__all__ = ["EmptyStateWidget", "ToastOverlay", "confirm_destructive_action"]
