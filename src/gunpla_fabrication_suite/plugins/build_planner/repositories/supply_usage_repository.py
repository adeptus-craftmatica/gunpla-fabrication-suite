"""Repository for :class:`SupplyUsage` rows."""

from __future__ import annotations

from sqlalchemy import select

from gunpla_fabrication_suite.core.persistence import DatabaseService
from gunpla_fabrication_suite.plugins.build_planner.models.supply_usage import SupplyUsage


class SupplyUsageRepository:
    """CRUD access to logged supply usages."""

    def __init__(self, database: DatabaseService) -> None:
        self._database = database

    def add(self, usage: SupplyUsage) -> SupplyUsage:
        """Insert a new supply usage."""
        with self._database.session() as session:
            session.add(usage)
            session.flush()
            session.refresh(usage)
            session.expunge(usage)
            return usage

    def get(self, usage_id: str) -> SupplyUsage | None:
        """Fetch a supply usage by id."""
        with self._database.session() as session:
            usage = session.get(SupplyUsage, usage_id)
            if usage is not None:
                session.expunge(usage)
            return usage

    def list_for_project(self, build_project_id: str) -> list[SupplyUsage]:
        """List a build's logged supply usages, newest first."""
        with self._database.session() as session:
            statement = (
                select(SupplyUsage)
                .where(SupplyUsage.build_project_id == build_project_id)
                .order_by(SupplyUsage.created_at.desc())
            )
            usages = list(session.scalars(statement))
            for usage in usages:
                session.expunge(usage)
            return usages

    def delete(self, usage_id: str) -> None:
        """Permanently remove a logged usage."""
        with self._database.session() as session:
            usage = session.get(SupplyUsage, usage_id)
            if usage is not None:
                session.delete(usage)
