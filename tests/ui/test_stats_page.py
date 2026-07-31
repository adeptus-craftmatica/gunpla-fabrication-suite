"""Tests for the Stats & Insights page."""

from __future__ import annotations

import pytest

from gunpla_fabrication_suite.plugins.kit_library.schemas import KitCreate
from gunpla_fabrication_suite.plugins.stats.services.stats_service import StatsService
from gunpla_fabrication_suite.plugins.stats.ui.stats_page import StatsPage


@pytest.fixture
def service(kit_service, build_service, work_session_service, supply_service, photo_service):
    return StatsService(
        kit_service, build_service, work_session_service, supply_service, photo_service
    )


@pytest.fixture
def page(qtbot, service):
    widget = StatsPage(service)
    qtbot.addWidget(widget)
    return widget


def test_page_starts_with_zeroed_tiles(page: StatsPage) -> None:
    assert page._status_table.rowCount() == 0
    assert page._grade_table.rowCount() == 0
    assert page._tiles_layout.count() == 4


def test_refresh_populates_breakdown_tables(kit_service, page: StatsPage, existing_kit) -> None:
    kit_service.create_kit(KitCreate(manufacturer="Bandai", name="Zaku II", grade="RG"))

    page.refresh()

    assert page._grade_table.rowCount() == 2
