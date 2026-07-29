"""Custom SQLAlchemy column types.

SQLite has no native timezone-aware storage: SQLAlchemy happily stores an
aware ``datetime`` but returns a *naive* one on read. Left unfixed, every
timestamp becomes naive the moment it round-trips through the database,
silently violating this project's "timezone-aware UTC internally" rule
(and breaking any arithmetic against a fresh ``datetime.now(UTC)``).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator[datetime]):
    """A ``DateTime`` column that always round-trips as timezone-aware UTC."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: object) -> datetime | None:
        """Normalize to aware UTC before handing the value to the DBAPI."""
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: object) -> datetime | None:
        """Restore UTC tzinfo on values the DBAPI returned as naive."""
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
