"""Pydantic DTOs for the Build Planner service boundary."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from gunpla_fabrication_suite.plugins.build_planner.models.enums import BuildStatus


class BuildProjectCreate(BaseModel):
    """Fields required to start a new build."""

    kit_id: str
    title: str = Field(min_length=1, max_length=200)
    template_key: str
    is_commission: bool = False


class BuildProjectRead(BaseModel):
    """A build project as returned to the UI layer, with computed progress."""

    model_config = {"from_attributes": True}

    id: str
    kit_id: str
    title: str
    template_key: str
    status: str
    is_commission: bool
    progress_override_percent: int | None
    is_progress_overridden: bool
    progress_percent: int
    started_at: datetime | None
    completed_at: datetime | None
    notes: str | None
    is_deleted: bool
    version: int
    created_at: datetime
    updated_at: datetime


class BuildStageRead(BaseModel):
    """A stage as returned to the UI layer."""

    model_config = {"from_attributes": True}

    id: str
    build_project_id: str
    name: str
    order_index: int
    weight: int
    is_completed: bool
    completed_at: datetime | None


class BuildTaskCreate(BaseModel):
    """Fields required to add a task to a stage."""

    title: str = Field(min_length=1, max_length=200)
    due_date: date | None = None
    estimated_hours: float | None = None
    notes: str | None = None


class BuildTaskRead(BaseModel):
    """A task as returned to the UI layer."""

    model_config = {"from_attributes": True}

    id: str
    build_stage_id: str
    title: str
    order_index: int
    is_completed: bool
    completed_at: datetime | None
    due_date: date | None
    estimated_hours: float | None
    actual_hours: float | None
    notes: str | None


class WorkSessionRead(BaseModel):
    """A work session as returned to the UI layer, with computed elapsed time."""

    model_config = {"from_attributes": True}

    id: str
    build_project_id: str
    build_stage_id: str | None
    build_task_id: str | None
    started_at: datetime
    ended_at: datetime | None
    paused_seconds: int
    is_running: bool
    is_paused: bool
    elapsed_seconds: int
    is_billable: bool
    rating: int | None
    notes: str | None


class JournalEntryCreate(BaseModel):
    """Fields required to add a journal entry."""

    note: str = Field(min_length=1)
    build_stage_id: str | None = None


class JournalEntryRead(BaseModel):
    """A journal entry as returned to the UI layer."""

    model_config = {"from_attributes": True}

    id: str
    build_project_id: str
    build_stage_id: str | None
    note: str
    created_at: datetime


class SupplyUsageCreate(BaseModel):
    """Fields required to log a supply's use on a build."""

    supply_id: str
    quantity_used: float = Field(gt=0)
    notes: str | None = None


class SupplyUsageRead(BaseModel):
    """A logged supply usage as returned to the UI layer."""

    model_config = {"from_attributes": True}

    id: str
    build_project_id: str
    supply_id: str
    quantity_used: float
    unit_snapshot: str
    unit_cost_cents_snapshot: int | None
    estimated_cost_cents: int | None
    notes: str | None
    created_at: datetime


__all__ = [
    "BuildProjectCreate",
    "BuildProjectRead",
    "BuildStageRead",
    "BuildStatus",
    "BuildTaskCreate",
    "BuildTaskRead",
    "JournalEntryCreate",
    "JournalEntryRead",
    "SupplyUsageCreate",
    "SupplyUsageRead",
    "WorkSessionRead",
]
