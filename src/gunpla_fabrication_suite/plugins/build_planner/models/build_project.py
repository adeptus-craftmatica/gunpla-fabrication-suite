"""The ``BuildProject`` ORM model: a kit being tracked from planning to completion."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from gunpla_fabrication_suite.core.persistence.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    VersionMixin,
)
from gunpla_fabrication_suite.core.persistence.types import UTCDateTime
from gunpla_fabrication_suite.plugins.build_planner.models.enums import BuildStatus


class BuildProject(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, Base):
    """A single build: a kit, a template's worth of stages, and its progress.

    ``kit_id`` intentionally has no SQL foreign key into
    ``kit_library_kits`` — Build Planner depends on the Kit Library plugin's
    *service* (resolved through the shared service container), never on its
    tables directly. The id is validated at the service layer instead.
    """

    __tablename__ = "build_planner_projects"

    kit_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    template_key: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, default=BuildStatus.PLANNING.value
    )
    is_commission: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    progress_override_percent: Mapped[int | None] = mapped_column(Integer, default=None)

    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)

    @property
    def is_progress_overridden(self) -> bool:
        """Whether a manual progress override is currently active."""
        return self.progress_override_percent is not None
