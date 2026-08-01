"""Checking GitHub's public Releases API for a newer version.

Runs via :class:`BackgroundJobManager`, matching the pattern in
``core/auto_backup.py``: the worker thread does only pure network I/O
(:func:`check_for_update`), and the settings write happens back on the main
thread, in a slot connected to the job manager's signals, so nothing ever
mutates :class:`SettingsService` from a worker thread.

Unlike a failed automatic backup (a data-safety concern worth surfacing),
a failed startup update check is expected and frequent — offline, a
transient GitHub outage, or a rate limit — and isn't user-actionable, so
:func:`maybe_check_for_update_on_startup` stays silent on failure. The
manual, button-triggered :func:`check_for_update_now` always gives
feedback instead, since a deliberate click deserves a response either way.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from gunpla_fabrication_suite.core.jobs import BackgroundJobManager, JobHandle
from gunpla_fabrication_suite.core.logging import get_logger
from gunpla_fabrication_suite.core.notifications import NotificationCenter, NotificationSeverity
from gunpla_fabrication_suite.core.settings import SettingsService

_logger = get_logger("update_check")

_REPO = "adeptus-craftmatica/gunpla-fabrication-suite"
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def parse_version(text: str) -> tuple[int, int, int] | None:
    """Parse an ``X.Y.Z`` version string (an optional leading ``v`` is stripped).

    Returns ``None`` for anything that doesn't match — a malformed or
    pre-release tag should never crash the comparison, just be treated as
    "not newer".
    """
    candidate = text.strip().lstrip("v")
    if not _VERSION_RE.match(candidate):
        return None
    major, minor, patch = candidate.split(".")
    return (int(major), int(minor), int(patch))


def _fetch_latest_release(repo: str = _REPO) -> dict[str, Any] | None:
    """Fetch the latest release payload from GitHub, or ``None`` on any failure."""
    try:
        response = httpx.get(
            f"https://api.github.com/repos/{repo}/releases/latest", timeout=5.0
        )
    except httpx.HTTPError:
        return None
    if response.status_code != 200:
        return None
    try:
        payload: dict[str, Any] = response.json()
    except ValueError:
        return None
    return payload


@dataclass(frozen=True, slots=True)
class UpdateCheckResult:
    """The outcome of a completed (successful) update check."""

    latest_version: str
    html_url: str
    is_newer: bool


def check_for_update(current_version: str, repo: str = _REPO) -> UpdateCheckResult | None:
    """Check GitHub for the latest release. Runs on a worker thread.

    Returns ``None`` if the check couldn't complete at all (offline, rate
    limited, malformed response) — never raises.
    """
    payload = _fetch_latest_release(repo)
    if payload is None:
        return None

    tag_name = payload.get("tag_name")
    html_url = payload.get("html_url")
    if not isinstance(tag_name, str) or not isinstance(html_url, str):
        return None

    latest_version = tag_name.lstrip("v")
    latest_parsed = parse_version(latest_version)
    current_parsed = parse_version(current_version)
    is_newer = (
        latest_parsed is not None
        and current_parsed is not None
        and latest_parsed > current_parsed
    )
    return UpdateCheckResult(latest_version=latest_version, html_url=html_url, is_newer=is_newer)


def _record_check_result(
    settings_service: SettingsService, result: UpdateCheckResult | None
) -> None:
    settings = settings_service.current
    settings.update_check.last_checked_at = datetime.now(UTC).isoformat()
    if result is not None:
        settings.update_check.last_known_version = result.latest_version
    settings_service.save(settings)


def maybe_check_for_update_on_startup(
    settings_service: SettingsService,
    jobs: BackgroundJobManager,
    notifications: NotificationCenter,
    current_version: str,
) -> None:
    """Submit a background update check, if enabled. Call once at startup.

    Silent on failure and when no newer version is found — only posts a
    toast when a genuinely newer version is discovered.
    """
    if not settings_service.current.update_check.enabled:
        return

    handle = jobs.submit("update_check", lambda _report_progress: check_for_update(current_version))

    def _on_succeeded(job_id: str, result: object) -> None:
        if job_id != handle.id:
            return
        jobs.job_succeeded.disconnect(_on_succeeded)
        jobs.job_failed.disconnect(_on_failed)
        outcome: UpdateCheckResult | None = result  # type: ignore[assignment]
        _record_check_result(settings_service, outcome)
        if outcome is not None and outcome.is_newer:
            _logger.info("update_available", version=outcome.latest_version)
            notifications.post(
                f"Version {outcome.latest_version} is available. See the About page for details.",
                severity=NotificationSeverity.INFO,
                source="update_check",
            )

    def _on_failed(job_id: str, error: str) -> None:
        if job_id != handle.id:
            return
        jobs.job_succeeded.disconnect(_on_succeeded)
        jobs.job_failed.disconnect(_on_failed)
        _logger.warning("update_check_failed", error=error)

    jobs.job_succeeded.connect(_on_succeeded)
    jobs.job_failed.connect(_on_failed)


def check_for_update_now(
    settings_service: SettingsService,
    jobs: BackgroundJobManager,
    notifications: NotificationCenter,
    current_version: str,
) -> JobHandle:
    """Submit a background update check unconditionally. Call from a UI button.

    Always posts a toast, regardless of outcome — a deliberate click
    deserves feedback either way, unlike the quiet startup check. Returns
    the job handle so a caller (e.g. the About page) can track completion
    of this specific check without misreading an unrelated job's signal.
    """
    handle = jobs.submit("update_check", lambda _report_progress: check_for_update(current_version))

    def _on_succeeded(job_id: str, result: object) -> None:
        if job_id != handle.id:
            return
        jobs.job_succeeded.disconnect(_on_succeeded)
        jobs.job_failed.disconnect(_on_failed)
        outcome: UpdateCheckResult | None = result  # type: ignore[assignment]
        _record_check_result(settings_service, outcome)
        if outcome is None:
            notifications.post(
                "Couldn't check for updates. Check your connection and try again.",
                severity=NotificationSeverity.WARNING,
                source="update_check",
            )
        elif outcome.is_newer:
            notifications.post(
                f"Version {outcome.latest_version} is available. See the About page for details.",
                severity=NotificationSeverity.INFO,
                source="update_check",
            )
        else:
            notifications.post(
                "You're running the latest version.",
                severity=NotificationSeverity.SUCCESS,
                source="update_check",
            )

    def _on_failed(job_id: str, error: str) -> None:
        if job_id != handle.id:
            return
        jobs.job_succeeded.disconnect(_on_succeeded)
        jobs.job_failed.disconnect(_on_failed)
        _logger.warning("update_check_failed", error=error)
        notifications.post(
            "Couldn't check for updates. Check your connection and try again.",
            severity=NotificationSeverity.WARNING,
            source="update_check",
        )

    jobs.job_succeeded.connect(_on_succeeded)
    jobs.job_failed.connect(_on_failed)
    return handle
