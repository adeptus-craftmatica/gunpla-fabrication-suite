"""The ``SupplyUsage`` ORM model: a supply logged as used on a build.

``supply_id`` intentionally has no SQL foreign key into ``supplies_items`` —
same reasoning as ``BuildProject.kit_id``: Build Planner depends on the
Supplies plugin's *service* (resolved through the shared service container),
never on its tables directly. The id is validated at the service layer
instead.

Rows are immutable log entries (added or hard-deleted, never edited in
place), same as ``WorkSession``/``BuildJournalEntry`` — hence no
``SoftDeleteMixin``/``VersionMixin``. ``unit_cost_cents_snapshot`` and
``estimated_cost_cents`` are frozen at creation time rather than recomputed
later, since a supply's price/quantity can drift after the fact.
"""

from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from gunpla_fabrication_suite.core.persistence.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class SupplyUsage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single record of a supply being consumed on a build."""

    __tablename__ = "build_planner_supply_usages"

    build_project_id: Mapped[str] = mapped_column(
        ForeignKey("build_planner_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    supply_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    quantity_used: Mapped[float] = mapped_column(Float, nullable=False)
    unit_snapshot: Mapped[str] = mapped_column(String(20), nullable=False)
    unit_cost_cents_snapshot: Mapped[int | None] = mapped_column(Integer, default=None)
    estimated_cost_cents: Mapped[int | None] = mapped_column(Integer, default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
