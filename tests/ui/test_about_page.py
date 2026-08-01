"""Tests for the Updates page: version display, manual check, and its startup toggle."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt

from gunpla_fabrication_suite import __version__
from gunpla_fabrication_suite.core.notifications import NotificationCenter
from gunpla_fabrication_suite.core.update_check import UpdateCheckResult
from gunpla_fabrication_suite.shell import about_page as about_page_module
from gunpla_fabrication_suite.shell.about_page import AboutPage


@pytest.fixture
def notifications() -> NotificationCenter:
    return NotificationCenter()


@pytest.fixture
def page(qtbot, settings_service, jobs, notifications) -> AboutPage:
    widget = AboutPage(settings_service, jobs, notifications)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.wait(10)
    return widget


def test_page_shows_current_version(page: AboutPage) -> None:
    assert page._version_label.text() == f"Version {__version__}"


def test_page_constructs_with_expected_controls(page: AboutPage) -> None:
    assert page._check_button.text() == "Check for Updates"
    assert page._auto_check_checkbox.isChecked() is True  # default is on, per settings default


def test_never_checked_status_shown_by_default(page: AboutPage) -> None:
    assert page._status_label.text() == "Never checked for updates."
    assert page._view_release_button.isVisible() is False


def test_toggling_checkbox_persists_via_settings(page: AboutPage, settings_service) -> None:
    page._auto_check_checkbox.setChecked(False)

    assert settings_service.current.update_check.enabled is False


def test_status_reflects_a_known_newer_version_at_construction(
    qtbot, settings_service, jobs, notifications
) -> None:
    settings = settings_service.current
    settings.update_check.last_checked_at = "2026-01-01T00:00:00+00:00"
    settings.update_check.last_known_version = "99.0.0"
    settings_service.save(settings)

    widget = AboutPage(settings_service, jobs, notifications)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.wait(10)

    assert widget._status_label.text() == "Version 99.0.0 is available."
    assert widget._view_release_button.isVisible() is True


def test_status_reflects_up_to_date_at_construction(
    qtbot, settings_service, jobs, notifications
) -> None:
    settings = settings_service.current
    settings.update_check.last_checked_at = "2026-01-01T00:00:00+00:00"
    settings.update_check.last_known_version = __version__
    settings_service.save(settings)

    widget = AboutPage(settings_service, jobs, notifications)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.wait(10)

    assert widget._status_label.text() == "You're running the latest version."
    assert widget._view_release_button.isVisible() is False


def test_clicking_check_button_disables_it_then_restores_it_on_completion(
    qtbot, monkeypatch, page: AboutPage, settings_service, jobs, notifications
) -> None:
    monkeypatch.setattr(
        about_page_module,
        "check_for_update_now",
        lambda settings_service, jobs, notifications, current_version: jobs.submit(
            "update_check",
            lambda _report_progress: UpdateCheckResult(
                latest_version="5.0.0", html_url="https://example.com", is_newer=True
            ),
        ),
    )

    qtbot.mouseClick(page._check_button, Qt.MouseButton.LeftButton)

    assert page._check_button.isEnabled() is False
    assert page._check_button.text() == "Checking…"

    qtbot.waitUntil(lambda: page._check_button.isEnabled(), timeout=2000)
    assert page._check_button.text() == "Check for Updates"
