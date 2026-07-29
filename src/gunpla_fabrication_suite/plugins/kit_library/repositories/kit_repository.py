"""Repository for :class:`Kit` rows.

The repository is the only place in this plugin that issues SQLAlchemy
queries; the service layer and UI never do.
"""

from __future__ import annotations

from sqlalchemy import func, select

from gunpla_fabrication_suite.core.persistence import DatabaseService
from gunpla_fabrication_suite.plugins.kit_library.models.kit import Kit


class KitRepository:
    """CRUD access to the ``kit_library_kits`` table."""

    def __init__(self, database: DatabaseService) -> None:
        self._database = database

    def add(self, kit: Kit) -> Kit:
        """Insert a new kit and return it with generated fields populated."""
        with self._database.session() as session:
            session.add(kit)
            session.flush()
            session.refresh(kit)
            session.expunge(kit)
            return kit

    def get(self, kit_id: str) -> Kit | None:
        """Fetch a kit by id, including soft-deleted ones."""
        with self._database.session() as session:
            kit = session.get(Kit, kit_id)
            if kit is not None:
                session.expunge(kit)
            return kit

    def list_all(self, *, include_archived: bool = False) -> list[Kit]:
        """List every kit, ordered by most recently updated first."""
        with self._database.session() as session:
            statement = select(Kit).order_by(Kit.updated_at.desc())
            if not include_archived:
                statement = statement.where(Kit.deleted_at.is_(None))
            kits = list(session.scalars(statement))
            for kit in kits:
                session.expunge(kit)
            return kits

    def update(self, kit: Kit) -> Kit:
        """Merge changes to an existing kit back into the database."""
        with self._database.session() as session:
            merged = session.merge(kit)
            session.flush()
            session.refresh(merged)
            session.expunge(merged)
            return merged

    def count_active(self) -> int:
        """The number of kits not soft-deleted, for dashboard widgets."""
        with self._database.session() as session:
            statement = select(func.count()).select_from(Kit).where(Kit.deleted_at.is_(None))
            return session.scalar(statement) or 0
