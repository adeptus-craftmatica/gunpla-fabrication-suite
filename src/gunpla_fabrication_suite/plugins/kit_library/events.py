"""Domain events published by the Kit Library plugin.

Other plugins subscribe to these instead of importing Kit Library's
repository or ORM model — this is the stable, cross-plugin contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class KitAdded:
    """A new kit was added to the collection or backlog."""

    kit_id: str
    name: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class KitUpdated:
    """An existing kit's fields changed."""

    kit_id: str
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class KitArchived:
    """A kit was soft-deleted (archived) out of the active collection."""

    kit_id: str
