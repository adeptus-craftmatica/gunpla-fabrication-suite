"""Tests for the work-session timer: start/pause/resume/stop and manual logging."""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

import pytest

from gunpla_fabrication_suite.core.events import EventBus
from gunpla_fabrication_suite.plugins.build_planner.errors import (
    WorkSessionAlreadyRunningError,
    WorkSessionNotFoundError,
)
from gunpla_fabrication_suite.plugins.build_planner.events import (
    WorkSessionCompleted,
    WorkSessionStarted,
)
from gunpla_fabrication_suite.plugins.build_planner.schemas import BuildProjectCreate
from gunpla_fabrication_suite.plugins.build_planner.services.build_service import BuildService
from gunpla_fabrication_suite.plugins.build_planner.services.work_session_service import (
    WorkSessionService,
)
from gunpla_fabrication_suite.plugins.kit_library.schemas import KitRead


@pytest.fixture
def build_id(build_service: BuildService, existing_kit: KitRead) -> str:
    build = build_service.create_build(
        BuildProjectCreate(
            kit_id=existing_kit.id, title="Timer Test Build", template_key="straight_build"
        )
    )
    return build.id


def test_start_timer_creates_running_session(
    work_session_service: WorkSessionService, build_id: str, event_bus: EventBus
) -> None:
    events: list[WorkSessionStarted] = []
    event_bus.subscribe(WorkSessionStarted, events.append)

    session = work_session_service.start_timer(build_id)

    assert session.is_running is True
    assert session.is_paused is False
    assert len(events) == 1


def test_cannot_start_a_second_timer_while_one_is_running(
    work_session_service: WorkSessionService, build_id: str
) -> None:
    work_session_service.start_timer(build_id)

    with pytest.raises(WorkSessionAlreadyRunningError):
        work_session_service.start_timer(build_id)


def test_get_active_session_returns_none_when_idle(
    work_session_service: WorkSessionService,
) -> None:
    assert work_session_service.get_active_session() is None


def test_pause_marks_session_as_paused_and_stops_elapsed_growth(
    work_session_service: WorkSessionService, build_id: str
) -> None:
    session = work_session_service.start_timer(build_id)

    paused = work_session_service.pause_timer(session.id)
    assert paused.is_paused is True

    elapsed_at_pause = paused.elapsed_seconds
    time.sleep(0.3)
    still_paused = work_session_service.get_active_session()
    assert still_paused is not None
    # Elapsed should not have grown meaningfully while paused.
    assert still_paused.elapsed_seconds <= elapsed_at_pause + 1


def test_resume_continues_accumulating_elapsed_time(
    work_session_service: WorkSessionService, build_id: str
) -> None:
    session = work_session_service.start_timer(build_id)
    work_session_service.pause_timer(session.id)
    resumed = work_session_service.resume_timer(session.id)

    assert resumed.is_paused is False
    assert resumed.is_running is True


def test_stop_timer_finalizes_session_and_publishes_event(
    work_session_service: WorkSessionService, build_id: str, event_bus: EventBus
) -> None:
    completed_events: list[WorkSessionCompleted] = []
    event_bus.subscribe(WorkSessionCompleted, completed_events.append)

    session = work_session_service.start_timer(build_id)
    time.sleep(1.1)
    stopped = work_session_service.stop_timer(session.id, notes="done", is_billable=True)

    assert stopped.is_running is False
    assert stopped.notes == "done"
    assert stopped.is_billable is True
    assert stopped.elapsed_seconds >= 1
    assert len(completed_events) == 1
    assert completed_events[0].duration_seconds >= 1

    assert work_session_service.get_active_session() is None


def test_stop_unknown_session_raises(work_session_service: WorkSessionService) -> None:
    with pytest.raises(WorkSessionNotFoundError):
        work_session_service.stop_timer("missing")


def test_log_manual_session_creates_completed_session(
    work_session_service: WorkSessionService, build_id: str
) -> None:
    now = datetime.now(UTC)
    session = work_session_service.log_manual_session(
        build_id, started_at=now - timedelta(hours=2), ended_at=now, notes="retroactive"
    )

    assert session.is_running is False
    assert session.elapsed_seconds == pytest.approx(2 * 3600, abs=2)


def test_total_hours_sums_only_finished_sessions(
    work_session_service: WorkSessionService, build_id: str
) -> None:
    now = datetime.now(UTC)
    work_session_service.log_manual_session(
        build_id, started_at=now - timedelta(hours=1), ended_at=now
    )
    work_session_service.start_timer(build_id)  # still running, should not count

    assert work_session_service.total_hours(build_id) == pytest.approx(1.0, abs=0.01)


def test_starting_a_second_build_timer_after_stopping_the_first_succeeds(
    work_session_service: WorkSessionService, build_service: BuildService, existing_kit: KitRead
) -> None:
    build_a = build_service.create_build(
        BuildProjectCreate(kit_id=existing_kit.id, title="A", template_key="straight_build")
    )
    build_b = build_service.create_build(
        BuildProjectCreate(kit_id=existing_kit.id, title="B", template_key="straight_build")
    )

    session_a = work_session_service.start_timer(build_a.id)
    work_session_service.stop_timer(session_a.id)

    session_b = work_session_service.start_timer(build_b.id)
    assert session_b.build_project_id == build_b.id
