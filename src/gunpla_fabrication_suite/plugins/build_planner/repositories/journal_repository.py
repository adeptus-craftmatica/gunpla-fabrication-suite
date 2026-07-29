"""Repository for :class:`BuildJournalEntry` rows."""

from __future__ import annotations

from sqlalchemy import select

from gunpla_fabrication_suite.core.persistence import DatabaseService
from gunpla_fabrication_suite.plugins.build_planner.models.journal_entry import BuildJournalEntry


class JournalRepository:
    """CRUD access to build journal entries."""

    def __init__(self, database: DatabaseService) -> None:
        self._database = database

    def add(self, entry: BuildJournalEntry) -> BuildJournalEntry:
        """Insert a new journal entry."""
        with self._database.session() as session:
            session.add(entry)
            session.flush()
            session.refresh(entry)
            session.expunge(entry)
            return entry

    def list_for_project(self, build_project_id: str) -> list[BuildJournalEntry]:
        """List a build's journal entries, newest first."""
        with self._database.session() as session:
            statement = (
                select(BuildJournalEntry)
                .where(BuildJournalEntry.build_project_id == build_project_id)
                .order_by(BuildJournalEntry.created_at.desc())
            )
            entries = list(session.scalars(statement))
            for entry in entries:
                session.expunge(entry)
            return entries
