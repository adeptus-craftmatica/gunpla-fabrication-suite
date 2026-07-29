"""The ``BuildJournalEntry`` ORM model: a timestamped note on a build's progress.

Photo attachments are deferred to the Photography plugin milestone; entries
are text-only for now.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from gunpla_fabrication_suite.core.persistence.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class BuildJournalEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single journal note, optionally tied to a specific stage."""

    __tablename__ = "build_planner_journal_entries"

    build_project_id: Mapped[str] = mapped_column(
        ForeignKey("build_planner_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    build_stage_id: Mapped[str | None] = mapped_column(
        ForeignKey("build_planner_stages.id", ondelete="SET NULL"), default=None
    )
    note: Mapped[str] = mapped_column(Text, nullable=False)
