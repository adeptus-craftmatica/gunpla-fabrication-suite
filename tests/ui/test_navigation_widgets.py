"""Regression tests: a page title containing "&" must render literally, not as
a stray mnemonic-underline artifact (QPushButton treats a bare "&" as an
accelerator marker).
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from gunpla_fabrication_suite.plugin_sdk.contracts import NavigationPageContribution
from gunpla_fabrication_suite.plugin_sdk.registries import NavigationRegistry
from gunpla_fabrication_suite.shell.navigation.compact_rail import CompactRail, _compact_label
from gunpla_fabrication_suite.shell.navigation.rail import NavigationRail
from gunpla_fabrication_suite.shell.navigation.top_bar import TopNavBar

_TITLE = "Stats & Insights"


def _registry_with(title: str) -> NavigationRegistry:
    registry = NavigationRegistry()
    registry.register(
        "test_plugin",
        NavigationPageContribution(page_id="stats", title=title, factory=lambda: QWidget()),
    )
    return registry


def test_navigation_rail_escapes_ampersand_in_button_text(qtbot) -> None:
    rail = NavigationRail(_registry_with(_TITLE))
    qtbot.addWidget(rail)

    assert rail._buttons["stats"].text() == "Stats && Insights"


def test_top_nav_bar_escapes_ampersand_in_button_text(qtbot) -> None:
    bar = TopNavBar(_registry_with(_TITLE))
    qtbot.addWidget(bar)

    assert bar._buttons["stats"].text() == "Stats && Insights"


def test_compact_label_skips_bare_connector_words() -> None:
    assert _compact_label(_TITLE) == "SI"


def test_compact_rail_button_text_has_no_stray_ampersand(qtbot) -> None:
    rail = CompactRail(_registry_with(_TITLE))
    qtbot.addWidget(rail)

    assert "&" not in rail._buttons["stats"].text()
