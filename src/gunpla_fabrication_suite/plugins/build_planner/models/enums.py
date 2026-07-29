"""Enumerations shared across Build Planner models."""

from __future__ import annotations

from enum import StrEnum


class BuildStatus(StrEnum):
    """Where a build project sits in its lifecycle.

    Stored as plain text (not a native SQL enum) so statuses can become
    user-customizable in a future milestone without a schema change —
    matching the same decision made for ``kit_library.CollectionStatus``.
    """

    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    WAITING_ON_SUPPLIES = "waiting_on_supplies"
    WAITING_ON_REPLACEMENT_PARTS = "waiting_on_replacement_parts"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
