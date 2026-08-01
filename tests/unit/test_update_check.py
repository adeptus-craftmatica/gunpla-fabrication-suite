"""Tests for the startup/manual GitHub-release update check."""

from __future__ import annotations

import httpx

from gunpla_fabrication_suite.core.notifications import NotificationCenter, NotificationSeverity
from gunpla_fabrication_suite.core.update_check import (
    UpdateCheckResult,
    check_for_update,
    check_for_update_now,
    maybe_check_for_update_on_startup,
    parse_version,
)


def test_parse_version_accepts_plain_and_v_prefixed() -> None:
    assert parse_version("4.1.0") == (4, 1, 0)
    assert parse_version("v4.1.0") == (4, 1, 0)


def test_parse_version_rejects_malformed_strings() -> None:
    assert parse_version("latest") is None
    assert parse_version("") is None
    assert parse_version("4.1") is None


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> dict:
        return self._payload


def test_check_for_update_reports_newer_version_available(monkeypatch) -> None:
    monkeypatch.setattr(
        httpx,
        "get",
        lambda *a, **k: _FakeResponse(
            200,
            {
                "tag_name": "v5.0.0",
                "html_url": "https://github.com/example/example/releases/tag/v5.0.0",
            },
        ),
    )

    result = check_for_update("4.0.1")

    assert result is not None
    assert result.latest_version == "5.0.0"
    assert result.is_newer is True


def test_check_for_update_reports_not_newer_when_same_version(monkeypatch) -> None:
    monkeypatch.setattr(
        httpx,
        "get",
        lambda *a, **k: _FakeResponse(
            200, {"tag_name": "v4.0.1", "html_url": "https://example.com/v4.0.1"}
        ),
    )

    result = check_for_update("4.0.1")

    assert result is not None
    assert result.is_newer is False


def test_check_for_update_reports_not_newer_when_current_is_ahead(monkeypatch) -> None:
    monkeypatch.setattr(
        httpx,
        "get",
        lambda *a, **k: _FakeResponse(
            200, {"tag_name": "v3.0.0", "html_url": "https://example.com/v3.0.0"}
        ),
    )

    result = check_for_update("4.0.1")

    assert result is not None
    assert result.is_newer is False


def test_check_for_update_returns_none_on_non_200(monkeypatch) -> None:
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(404))

    assert check_for_update("4.0.1") is None


def test_check_for_update_returns_none_on_network_error(monkeypatch) -> None:
    def _raise(*args: object, **kwargs: object) -> None:
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx, "get", _raise)

    assert check_for_update("4.0.1") is None


def test_maybe_check_on_startup_does_nothing_when_disabled(
    monkeypatch, settings_service, jobs
) -> None:
    settings = settings_service.current
    settings.update_check.enabled = False
    settings_service.save(settings)
    notifications = NotificationCenter()

    called = False

    def _fail(*args: object, **kwargs: object) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr("gunpla_fabrication_suite.core.update_check.check_for_update", _fail)

    maybe_check_for_update_on_startup(settings_service, jobs, notifications, "4.0.1")

    assert called is False
    assert notifications.history() == ()


def test_maybe_check_on_startup_notifies_when_newer_found(
    qtbot, monkeypatch, settings_service, jobs
) -> None:
    settings = settings_service.current
    settings.update_check.enabled = True
    settings_service.save(settings)
    notifications = NotificationCenter()

    monkeypatch.setattr(
        "gunpla_fabrication_suite.core.update_check.check_for_update",
        lambda current_version: UpdateCheckResult(
            latest_version="5.0.0", html_url="https://example.com", is_newer=True
        ),
    )

    maybe_check_for_update_on_startup(settings_service, jobs, notifications, "4.0.1")

    qtbot.waitUntil(lambda: len(notifications.history()) > 0, timeout=2000)

    assert notifications.history()[-1].severity == NotificationSeverity.INFO
    assert "5.0.0" in notifications.history()[-1].message
    assert settings_service.current.update_check.last_known_version == "5.0.0"
    assert settings_service.current.update_check.last_checked_at is not None


def test_maybe_check_on_startup_stays_silent_when_up_to_date(
    qtbot, monkeypatch, settings_service, jobs
) -> None:
    settings = settings_service.current
    settings.update_check.enabled = True
    settings_service.save(settings)
    notifications = NotificationCenter()

    monkeypatch.setattr(
        "gunpla_fabrication_suite.core.update_check.check_for_update",
        lambda current_version: UpdateCheckResult(
            latest_version="4.0.1", html_url="https://example.com", is_newer=False
        ),
    )

    maybe_check_for_update_on_startup(settings_service, jobs, notifications, "4.0.1")

    qtbot.waitUntil(
        lambda: settings_service.current.update_check.last_checked_at is not None, timeout=2000
    )

    assert notifications.history() == ()


def test_maybe_check_on_startup_stays_silent_on_fetch_failure(
    qtbot, monkeypatch, settings_service, jobs
) -> None:
    """A graceful fetch failure (``check_for_update`` returning ``None``, e.g.
    offline) still counts as a completed check attempt from the job manager's
    point of view — it didn't raise — so ``last_checked_at`` is still recorded
    (just without a ``last_known_version``). Only a hard job exception skips
    the settings write entirely; ``check_for_update`` is designed to never
    raise, so that path is a defensive backstop rather than a common case.
    """
    settings = settings_service.current
    settings.update_check.enabled = True
    settings_service.save(settings)
    notifications = NotificationCenter()

    monkeypatch.setattr(
        "gunpla_fabrication_suite.core.update_check.check_for_update",
        lambda current_version: None,
    )

    maybe_check_for_update_on_startup(settings_service, jobs, notifications, "4.0.1")

    qtbot.waitUntil(
        lambda: settings_service.current.update_check.last_checked_at is not None, timeout=2000
    )
    assert notifications.history() == ()
    assert settings_service.current.update_check.last_known_version is None


def test_check_for_update_now_reports_update_available(
    qtbot, monkeypatch, settings_service, jobs
) -> None:
    notifications = NotificationCenter()
    monkeypatch.setattr(
        "gunpla_fabrication_suite.core.update_check.check_for_update",
        lambda current_version: UpdateCheckResult(
            latest_version="5.0.0", html_url="https://example.com", is_newer=True
        ),
    )

    check_for_update_now(settings_service, jobs, notifications, "4.0.1")

    qtbot.waitUntil(lambda: len(notifications.history()) > 0, timeout=2000)
    assert notifications.history()[-1].severity == NotificationSeverity.INFO


def test_check_for_update_now_reports_up_to_date(
    qtbot, monkeypatch, settings_service, jobs
) -> None:
    notifications = NotificationCenter()
    monkeypatch.setattr(
        "gunpla_fabrication_suite.core.update_check.check_for_update",
        lambda current_version: UpdateCheckResult(
            latest_version="4.0.1", html_url="https://example.com", is_newer=False
        ),
    )

    check_for_update_now(settings_service, jobs, notifications, "4.0.1")

    qtbot.waitUntil(lambda: len(notifications.history()) > 0, timeout=2000)
    assert notifications.history()[-1].severity == NotificationSeverity.SUCCESS


def test_check_for_update_now_reports_failure(qtbot, monkeypatch, settings_service, jobs) -> None:
    notifications = NotificationCenter()
    monkeypatch.setattr(
        "gunpla_fabrication_suite.core.update_check.check_for_update",
        lambda current_version: None,
    )

    check_for_update_now(settings_service, jobs, notifications, "4.0.1")

    qtbot.waitUntil(lambda: len(notifications.history()) > 0, timeout=2000)
    assert notifications.history()[-1].severity == NotificationSeverity.WARNING
