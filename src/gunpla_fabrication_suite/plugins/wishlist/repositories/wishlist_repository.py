"""Repository for :class:`WishlistItem` rows.

The repository is the only place in this plugin that issues SQLAlchemy
queries; the service layer and UI never do.
"""

from __future__ import annotations

from sqlalchemy import func, select

from gunpla_fabrication_suite.core.persistence import DatabaseService
from gunpla_fabrication_suite.plugins.wishlist.models.wishlist_item import WishlistItem


class WishlistRepository:
    """CRUD access to the ``wishlist_items`` table."""

    def __init__(self, database: DatabaseService) -> None:
        self._database = database

    def add(self, item: WishlistItem) -> WishlistItem:
        """Insert a new wishlist item and return it with generated fields populated."""
        with self._database.session() as session:
            session.add(item)
            session.flush()
            session.refresh(item)
            session.expunge(item)
            return item

    def get(self, item_id: str) -> WishlistItem | None:
        """Fetch a wishlist item by id, including soft-deleted ones."""
        with self._database.session() as session:
            item = session.get(WishlistItem, item_id)
            if item is not None:
                session.expunge(item)
            return item

    def list_all(
        self, *, include_archived: bool = False, include_purchased: bool = False
    ) -> list[WishlistItem]:
        """List wishlist items, ordered by most recently updated first.

        Excludes archived and purchased items by default — the default view
        is "what I still want to buy."
        """
        with self._database.session() as session:
            statement = select(WishlistItem).order_by(WishlistItem.updated_at.desc())
            if not include_archived:
                statement = statement.where(WishlistItem.deleted_at.is_(None))
            if not include_purchased:
                statement = statement.where(WishlistItem.is_purchased.is_(False))
            items = list(session.scalars(statement))
            for item in items:
                session.expunge(item)
            return items

    def update(self, item: WishlistItem) -> WishlistItem:
        """Merge changes to an existing wishlist item back into the database."""
        with self._database.session() as session:
            merged = session.merge(item)
            session.flush()
            session.refresh(merged)
            session.expunge(merged)
            return merged

    def count_active(self) -> int:
        """The number of items still wanted (not archived, not purchased)."""
        with self._database.session() as session:
            statement = (
                select(func.count())
                .select_from(WishlistItem)
                .where(
                    WishlistItem.deleted_at.is_(None),
                    WishlistItem.is_purchased.is_(False),
                )
            )
            return session.scalar(statement) or 0
