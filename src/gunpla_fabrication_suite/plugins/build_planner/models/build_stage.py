"""The ``BuildStage`` ORM model: one step of a build project's plan."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from gunpla_fabrication_suite.core.persistence.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from gunpla_fabrication_suite.core.persistence.types import UTCDateTime


class BuildStage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A named, ordered, weighted step within one build project.

    Stages are materialized from a template when a build is created (see
    ``templates.py``) and are then fully editable per-project: reordered,
    renamed, added, or removed independently of the template they started
    from.
    """

    __tablename__ = "build_planner_stages"

    build_project_id: Mapped[str] = mapped_column(
        ForeignKey("build_planner_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
