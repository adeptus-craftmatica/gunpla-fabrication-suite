"""Domain events published by the Build Planner plugin.

Other plugins (Dashboard's "Continue Building" widget, and eventually
Calendar, Portfolio, Automation) subscribe to these instead of importing
Build Planner's repositories or ORM models.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class BuildCreated:
    """A new build project was created from a kit and a template."""

    build_id: str
    kit_id: str
    title: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class BuildStarted:
    """A build moved from Planning into active work."""

    build_id: str
    started_at: datetime


@dataclass(frozen=True, slots=True)
class BuildPaused:
    """A build was paused."""

    build_id: str


@dataclass(frozen=True, slots=True)
class BuildResumed:
    """A paused build resumed active work."""

    build_id: str


@dataclass(frozen=True, slots=True)
class BuildStageCompleted:
    """A stage within a build was marked complete."""

    build_id: str
    stage_id: str
    completed_at: datetime


@dataclass(frozen=True, slots=True)
class BuildCompleted:
    """Every stage in a build finished, or the user marked it complete."""

    build_id: str
    completed_at: datetime


@dataclass(frozen=True, slots=True)
class WorkSessionStarted:
    """A work session's timer started."""

    session_id: str
    build_id: str


@dataclass(frozen=True, slots=True)
class WorkSessionCompleted:
    """A work session's timer stopped."""

    session_id: str
    build_id: str
    duration_seconds: int


@dataclass(frozen=True, slots=True)
class SupplyUsageRecorded:
    """A supply was logged as used on a build, decrementing its stock."""

    usage_id: str
    build_id: str
    supply_id: str
    quantity_used: float
    created_at: datetime


@dataclass(frozen=True, slots=True)
class SupplyUsageDeleted:
    """A logged supply usage was removed, restoring its stock."""

    usage_id: str
    build_id: str
    supply_id: str
    quantity_used: float
