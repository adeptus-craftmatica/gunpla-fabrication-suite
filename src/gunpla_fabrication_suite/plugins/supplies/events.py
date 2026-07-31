"""Domain events published by the Supplies plugin.

Other plugins subscribe to these instead of importing Supplies' repository
or ORM model — this is the stable, cross-plugin contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SupplyAdded:
    """A new supply was added to the inventory."""

    supply_id: str
    name: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class SupplyUpdated:
    """An existing supply's fields changed."""

    supply_id: str
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class SupplyArchived:
    """A supply was soft-deleted (archived) out of the active inventory."""

    supply_id: str
