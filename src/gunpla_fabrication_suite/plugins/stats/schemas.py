"""A plain internal computed-value bundle — no external input to validate, unlike
every ``*Create`` schema elsewhere, so this is a dataclass rather than Pydantic.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StatsSnapshot:
    """A rolled-up snapshot of collection/build activity, computed on demand."""

    total_kits_owned: int
    kits_by_grade: dict[str, int]
    builds_by_status: dict[str, int]
    total_hours_built: float
    total_spent_cents: int
    total_photos: int
