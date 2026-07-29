"""The shared SQLAlchemy declarative base and reusable column mixins.

Every plugin's ORM models inherit from :class:`Base` so that a single
Alembic migration chain and a single SQLite file can serve the whole
application, while each plugin still owns its own table definitions and
migration scripts.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base shared by every plugin's ORM models."""


def utcnow() -> datetime:
    """Return the current, timezone-aware UTC timestamp."""
    return datetime.now(UTC)


class UUIDPrimaryKeyMixin:
    """Adds a UUID primary key stored as its 36-character string form."""

    id: Mapped[str] = mapped_column(
        primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False
    )


class TimestampMixin:
    """Adds timezone-aware ``created_at`` / ``updated_at`` columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class SoftDeleteMixin:
    """Adds a nullable ``deleted_at`` column for soft deletion."""

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    @property
    def is_deleted(self) -> bool:
        """Whether this record has been soft-deleted."""
        return self.deleted_at is not None


class VersionMixin:
    """Adds an integer ``version`` column for optimistic concurrency control."""

    version: Mapped[int] = mapped_column(default=1, nullable=False)
