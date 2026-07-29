"""Repository for :class:`WorkSession` rows."""

from __future__ import annotations

from sqlalchemy import select

from gunpla_fabrication_suite.core.persistence import DatabaseService
from gunpla_fabrication_suite.plugins.build_planner.models.work_session import WorkSession


class WorkSessionRepository:
    """CRUD and query access to logged work sessions."""

    def __init__(self, database: DatabaseService) -> None:
        self._database = database

    def add(self, session_row: WorkSession) -> WorkSession:
        """Insert a new work session."""
        with self._database.session() as session:
            session.add(session_row)
            session.flush()
            session.refresh(session_row)
            session.expunge(session_row)
            return session_row

    def get(self, session_id: str) -> WorkSession | None:
        """Fetch a work session by id."""
        with self._database.session() as session:
            row = session.get(WorkSession, session_id)
            if row is not None:
                session.expunge(row)
            return row

    def get_active(self) -> WorkSession | None:
        """Return the single work session that is still running, if any.

        The application only allows one running timer at a time, so this
        is how the UI (and a future restart) discovers "you left a timer
        running."
        """
        with self._database.session() as session:
            statement = select(WorkSession).where(WorkSession.ended_at.is_(None))
            row = session.scalars(statement).first()
            if row is not None:
                session.expunge(row)
            return row

    def list_for_project(self, build_project_id: str) -> list[WorkSession]:
        """List a build's sessions, most recently started first."""
        with self._database.session() as session:
            statement = (
                select(WorkSession)
                .where(WorkSession.build_project_id == build_project_id)
                .order_by(WorkSession.started_at.desc())
            )
            rows = list(session.scalars(statement))
            for row in rows:
                session.expunge(row)
            return rows

    def update(self, session_row: WorkSession) -> WorkSession:
        """Merge changes to an existing session back into the database."""
        with self._database.session() as session:
            merged = session.merge(session_row)
            session.flush()
            session.refresh(merged)
            session.expunge(merged)
            return merged
