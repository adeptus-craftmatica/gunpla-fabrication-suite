"""Repository for :class:`Supply` rows.

The repository is the only place in this plugin that issues SQLAlchemy
queries; the service layer and UI never do.
"""

from __future__ import annotations

from sqlalchemy import func, select

from gunpla_fabrication_suite.core.persistence import DatabaseService
from gunpla_fabrication_suite.plugins.supplies.models.supply import Supply


class SupplyRepository:
    """CRUD access to the ``supplies_items`` table."""

    def __init__(self, database: DatabaseService) -> None:
        self._database = database

    def add(self, supply: Supply) -> Supply:
        """Insert a new supply and return it with generated fields populated."""
        with self._database.session() as session:
            session.add(supply)
            session.flush()
            session.refresh(supply)
            session.expunge(supply)
            return supply

    def get(self, supply_id: str) -> Supply | None:
        """Fetch a supply by id, including soft-deleted ones."""
        with self._database.session() as session:
            supply = session.get(Supply, supply_id)
            if supply is not None:
                session.expunge(supply)
            return supply

    def list_all(self, *, include_archived: bool = False) -> list[Supply]:
        """List every supply, ordered by most recently updated first."""
        with self._database.session() as session:
            statement = select(Supply).order_by(Supply.updated_at.desc())
            if not include_archived:
                statement = statement.where(Supply.deleted_at.is_(None))
            supplies = list(session.scalars(statement))
            for supply in supplies:
                session.expunge(supply)
            return supplies

    def update(self, supply: Supply) -> Supply:
        """Merge changes to an existing supply back into the database."""
        with self._database.session() as session:
            merged = session.merge(supply)
            session.flush()
            session.refresh(merged)
            session.expunge(merged)
            return merged

    def count_active(self) -> int:
        """The number of supplies not soft-deleted, for dashboard widgets."""
        with self._database.session() as session:
            statement = select(func.count()).select_from(Supply).where(Supply.deleted_at.is_(None))
            return session.scalar(statement) or 0

    def count_low_stock(self) -> int:
        """The number of active supplies at or below their low-stock threshold."""
        with self._database.session() as session:
            statement = (
                select(func.count())
                .select_from(Supply)
                .where(
                    Supply.deleted_at.is_(None),
                    Supply.low_stock_threshold.is_not(None),
                    Supply.quantity_on_hand <= Supply.low_stock_threshold,
                )
            )
            return session.scalar(statement) or 0
