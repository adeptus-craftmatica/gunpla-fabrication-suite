"""Reusable, theme-aware widgets and dialogs shared across the shell and plugins."""

from __future__ import annotations

from gunpla_fabrication_suite.shared_ui.buttons import ButtonKind, set_button_kind
from gunpla_fabrication_suite.shared_ui.card import Card
from gunpla_fabrication_suite.shared_ui.confirm_dialog import confirm_destructive_action
from gunpla_fabrication_suite.shared_ui.empty_state import EmptyStateWidget
from gunpla_fabrication_suite.shared_ui.fuzzy_match import fuzzy_score
from gunpla_fabrication_suite.shared_ui.inspector_panel import InspectorPanel
from gunpla_fabrication_suite.shared_ui.labels import LabelRole, set_label_role
from gunpla_fabrication_suite.shared_ui.page_header import PageHeader
from gunpla_fabrication_suite.shared_ui.tables import configure_table_columns
from gunpla_fabrication_suite.shared_ui.toast import ToastOverlay
from gunpla_fabrication_suite.shared_ui.tokens import PAGE_TITLE, SPACING

__all__ = [
    "PAGE_TITLE",
    "SPACING",
    "ButtonKind",
    "Card",
    "EmptyStateWidget",
    "InspectorPanel",
    "LabelRole",
    "PageHeader",
    "ToastOverlay",
    "configure_table_columns",
    "confirm_destructive_action",
    "fuzzy_score",
    "set_button_kind",
    "set_label_role",
]
