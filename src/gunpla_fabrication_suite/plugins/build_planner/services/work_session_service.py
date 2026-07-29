"""Timer and work-session logging logic.

Elapsed time is always derived from wall-clock timestamps rather than an
in-memory countdown — see the module docstring on
:class:`~gunpla_fabrication_suite.plugins.build_planner.models.work_session.WorkSession`
for why that makes a running timer survive an application restart.
"""

from __future__ import annotations

from datetime import UTC, datetime

from gunpla_fabrication_suite.core.events import EventBus
from gunpla_fabrication_suite.plugins.build_planner.errors import (
    WorkSessionAlreadyRunningError,
    WorkSessionNotFoundError,
)
from gunpla_fabrication_suite.plugins.build_planner.events import (
    WorkSessionCompleted,
    WorkSessionStarted,
)
from gunpla_fabrication_suite.plugins.build_planner.models.work_session import WorkSession
from gunpla_fabrication_suite.plugins.build_planner.repositories.work_session_repository import (
    WorkSessionRepository,
)
from gunpla_fabrication_suite.plugins.build_planner.schemas import WorkSessionRead


class WorkSessionService:
    """Starts, pauses, resumes, and stops work-session timers."""

    def __init__(self, repository: WorkSessionRepository, events: EventBus) -> None:
        self._repository = repository
        self._events = events

    def start_timer(
        self, build_id: str, *, stage_id: str | None = None, task_id: str | None = None
    ) -> WorkSessionRead:
        """Start a new timer.

        Raises:
            WorkSessionAlreadyRunningError: If a timer is already running
                for any build — only one can run at a time.
        """
        active = self._repository.get_active()
        if active is not None:
            raise WorkSessionAlreadyRunningError(active.build_project_id)

        session_row = WorkSession(
            build_project_id=build_id,
            build_stage_id=stage_id,
            build_task_id=task_id,
            started_at=datetime.now(UTC),
        )
        saved = self._repository.add(session_row)
        self._events.publish(WorkSessionStarted(session_id=saved.id, build_id=build_id))
        return self._to_read(saved)

    def pause_timer(self, session_id: str) -> WorkSessionRead:
        """Pause a running timer.

        Raises:
            WorkSessionNotFoundError: If ``session_id`` does not exist.
        """
        session_row = self._require_session(session_id)
        if session_row.is_running and session_row.paused_at is None:
            session_row.paused_at = datetime.now(UTC)
            session_row = self._repository.update(session_row)
        return self._to_read(session_row)

    def resume_timer(self, session_id: str) -> WorkSessionRead:
        """Resume a paused timer.

        Raises:
            WorkSessionNotFoundError: If ``session_id`` does not exist.
        """
        session_row = self._require_session(session_id)
        if session_row.paused_at is not None:
            elapsed_pause = datetime.now(UTC) - session_row.paused_at
            session_row.paused_seconds += round(elapsed_pause.total_seconds())
            session_row.paused_at = None
            session_row = self._repository.update(session_row)
        return self._to_read(session_row)

    def stop_timer(
        self,
        session_id: str,
        *,
        notes: str | None = None,
        is_billable: bool = False,
        rating: int | None = None,
    ) -> WorkSessionRead:
        """Stop a timer, finalizing its elapsed duration.

        Raises:
            WorkSessionNotFoundError: If ``session_id`` does not exist.
        """
        session_row = self._require_session(session_id)
        now = datetime.now(UTC)

        if session_row.paused_at is not None:
            session_row.paused_seconds += round((now - session_row.paused_at).total_seconds())
            session_row.paused_at = None

        session_row.ended_at = now
        session_row.notes = notes
        session_row.is_billable = is_billable
        session_row.rating = rating
        saved = self._repository.update(session_row)

        duration_seconds = round((now - saved.started_at).total_seconds())
        duration_seconds = max(0, duration_seconds - saved.paused_seconds)
        self._events.publish(
            WorkSessionCompleted(
                session_id=saved.id,
                build_id=saved.build_project_id,
                duration_seconds=duration_seconds,
            )
        )
        return self._to_read(saved)

    def log_manual_session(
        self,
        build_id: str,
        *,
        started_at: datetime,
        ended_at: datetime,
        stage_id: str | None = None,
        task_id: str | None = None,
        notes: str | None = None,
        is_billable: bool = False,
    ) -> WorkSessionRead:
        """Log a completed session retroactively (no live timer involved)."""
        session_row = WorkSession(
            build_project_id=build_id,
            build_stage_id=stage_id,
            build_task_id=task_id,
            started_at=started_at,
            ended_at=ended_at,
            notes=notes,
            is_billable=is_billable,
        )
        saved = self._repository.add(session_row)
        return self._to_read(saved)

    def get_active_session(self) -> WorkSessionRead | None:
        """The single running (or paused-but-not-stopped) session, if any."""
        active = self._repository.get_active()
        return None if active is None else self._to_read(active)

    def list_sessions(self, build_id: str) -> list[WorkSessionRead]:
        """List a build's sessions, most recently started first."""
        rows = self._repository.list_for_project(build_id)
        return [self._to_read(row) for row in rows]

    def total_hours(self, build_id: str) -> float:
        """Total logged hours for a build, across finished sessions."""
        total_seconds = 0.0
        for row in self._repository.list_for_project(build_id):
            if row.ended_at is None:
                continue
            elapsed = (row.ended_at - row.started_at).total_seconds() - row.paused_seconds
            total_seconds += max(0, elapsed)
        return round(total_seconds / 3600, 2)

    def _require_session(self, session_id: str) -> WorkSession:
        session_row = self._repository.get(session_id)
        if session_row is None:
            raise WorkSessionNotFoundError(session_id)
        return session_row

    def _to_read(self, session_row: WorkSession) -> WorkSessionRead:
        elapsed_seconds = self._elapsed_seconds(session_row)
        return WorkSessionRead(
            id=session_row.id,
            build_project_id=session_row.build_project_id,
            build_stage_id=session_row.build_stage_id,
            build_task_id=session_row.build_task_id,
            started_at=session_row.started_at,
            ended_at=session_row.ended_at,
            paused_seconds=session_row.paused_seconds,
            is_running=session_row.is_running,
            is_paused=session_row.is_paused,
            elapsed_seconds=elapsed_seconds,
            is_billable=session_row.is_billable,
            rating=session_row.rating,
            notes=session_row.notes,
        )

    @staticmethod
    def _elapsed_seconds(session_row: WorkSession) -> int:
        end_point = session_row.ended_at or datetime.now(UTC)
        paused_seconds = session_row.paused_seconds
        if session_row.paused_at is not None:
            paused_seconds += round((end_point - session_row.paused_at).total_seconds())
        total = (end_point - session_row.started_at).total_seconds() - paused_seconds
        return max(0, round(total))
