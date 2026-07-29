"""Build journal logic: quick, timestamped notes on a build's progress."""

from __future__ import annotations

from gunpla_fabrication_suite.plugins.build_planner.models.journal_entry import BuildJournalEntry
from gunpla_fabrication_suite.plugins.build_planner.repositories.journal_repository import (
    JournalRepository,
)
from gunpla_fabrication_suite.plugins.build_planner.schemas import (
    JournalEntryCreate,
    JournalEntryRead,
)


class JournalService:
    """Adds and lists journal entries for a build."""

    def __init__(self, repository: JournalRepository) -> None:
        self._repository = repository

    def add_entry(self, build_id: str, data: JournalEntryCreate) -> JournalEntryRead:
        """Add a new journal entry to a build."""
        entry = BuildJournalEntry(
            build_project_id=build_id, build_stage_id=data.build_stage_id, note=data.note
        )
        saved = self._repository.add(entry)
        return JournalEntryRead.model_validate(saved)

    def list_entries(self, build_id: str) -> list[JournalEntryRead]:
        """List a build's journal entries, newest first."""
        entries = self._repository.list_for_project(build_id)
        return [JournalEntryRead.model_validate(entry) for entry in entries]
