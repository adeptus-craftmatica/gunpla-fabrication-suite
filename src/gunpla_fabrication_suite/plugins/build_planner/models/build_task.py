"""The ``BuildTask`` ORM model: a small, trackable unit of work within a stage."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from gunpla_fabrication_suite.core.persistence.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from gunpla_fabrication_suite.core.persistence.types import UTCDateTime


class BuildTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A checklist-style task within a stage, with optional hour tracking.

    Tasks are flat — no task-to-task dependency graph in this milestone.
    """

    __tablename__ = "build_planner_tasks"

    build_stage_id: Mapped[str] = mapped_column(
        ForeignKey("build_planner_stages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    due_date: Mapped[date | None] = mapped_column(Date, default=None)
    estimated_hours: Mapped[float | None] = mapped_column(default=None)
    actual_hours: Mapped[float | None] = mapped_column(default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
