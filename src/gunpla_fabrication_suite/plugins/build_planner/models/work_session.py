"""The ``WorkSession`` ORM model: a real or logged span of time spent building.

Elapsed time is always derived from wall-clock timestamps
(``started_at``, ``ended_at``, ``paused_seconds``) rather than an in-memory
countdown, so a running timer survives an application restart: on next
launch, whichever session has ``ended_at is None`` is still "running," and
its elapsed time is simply "now minus started_at minus paused_seconds."
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from gunpla_fabrication_suite.core.persistence.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from gunpla_fabrication_suite.core.persistence.types import UTCDateTime


class WorkSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single work session logged against a build (and optionally a stage/task)."""

    __tablename__ = "build_planner_work_sessions"

    build_project_id: Mapped[str] = mapped_column(
        ForeignKey("build_planner_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    build_stage_id: Mapped[str | None] = mapped_column(
        ForeignKey("build_planner_stages.id", ondelete="SET NULL"), default=None
    )
    build_task_id: Mapped[str | None] = mapped_column(
        ForeignKey("build_planner_tasks.id", ondelete="SET NULL"), default=None
    )

    started_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    paused_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    paused_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    is_billable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rating: Mapped[int | None] = mapped_column(Integer, default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)

    @property
    def is_running(self) -> bool:
        """Whether this session is still active (started, not yet stopped)."""
        return self.ended_at is None

    @property
    def is_paused(self) -> bool:
        """Whether this session is currently paused rather than actively running."""
        return self.is_running and self.paused_at is not None
