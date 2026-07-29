"""Tests for build creation, stage/task management, progress, and status transitions."""

from __future__ import annotations

import pytest

from gunpla_fabrication_suite.core.events import EventBus
from gunpla_fabrication_suite.plugins.build_planner.errors import (
    BuildNotFoundError,
    StageNotFoundError,
    TaskNotFoundError,
    UnknownTemplateError,
)
from gunpla_fabrication_suite.plugins.build_planner.events import (
    BuildCompleted,
    BuildCreated,
    BuildPaused,
    BuildResumed,
    BuildStageCompleted,
    BuildStarted,
)
from gunpla_fabrication_suite.plugins.build_planner.schemas import (
    BuildProjectCreate,
    BuildTaskCreate,
)
from gunpla_fabrication_suite.plugins.build_planner.services.build_service import BuildService
from gunpla_fabrication_suite.plugins.kit_library.schemas import KitRead
from gunpla_fabrication_suite.plugins.kit_library.services.kit_service import KitNotFoundError


def _create_payload(kit: KitRead, **overrides: object) -> BuildProjectCreate:
    defaults: dict[str, object] = {
        "kit_id": kit.id,
        "title": "My First Build",
        "template_key": "straight_build",
    }
    defaults.update(overrides)
    return BuildProjectCreate(**defaults)  # type: ignore[arg-type]


def test_create_build_materializes_template_stages(
    build_service: BuildService, existing_kit: KitRead
) -> None:
    build = build_service.create_build(_create_payload(existing_kit, template_key="panel_lined"))

    stages = build_service.list_stages(build.id)

    assert [s.name for s in stages] == [
        "Planning",
        "Runner Inspection",
        "Parts Washing",
        "Initial Assembly",
        "Panel Lining",
        "Final Assembly",
        "Photography",
        "Completed",
    ]
    assert build.progress_percent == 0
    assert build.status == "planning"


def test_create_build_raises_for_unknown_kit(build_service: BuildService) -> None:
    with pytest.raises(KitNotFoundError):
        build_service.create_build(
            BuildProjectCreate(kit_id="missing", title="X", template_key="straight_build")
        )


def test_create_build_raises_for_unknown_template(
    build_service: BuildService, existing_kit: KitRead
) -> None:
    with pytest.raises(UnknownTemplateError):
        build_service.create_build(_create_payload(existing_kit, template_key="not-a-template"))


def test_create_build_publishes_event(
    build_service: BuildService, existing_kit: KitRead, event_bus: EventBus
) -> None:
    events: list[BuildCreated] = []
    event_bus.subscribe(BuildCreated, events.append)

    build = build_service.create_build(_create_payload(existing_kit))

    assert len(events) == 1
    assert events[0].build_id == build.id


def test_progress_percent_is_weighted_by_stage_weight(
    build_service: BuildService, existing_kit: KitRead
) -> None:
    build = build_service.create_build(_create_payload(existing_kit))
    stages = build_service.list_stages(build.id)
    # Straight Build has 7 stages; give the first one triple weight.
    build_service.rename_stage(stages[0].id, name=stages[0].name, weight=300)

    build_service.toggle_stage_completion(stages[0].id, completed=True)
    build = build_service.get_build(build.id)

    # total weight = 300 + 6*100 = 900; completed weight = 300 -> 33%
    assert build.progress_percent == 33


def test_completing_all_stages_auto_completes_build(
    build_service: BuildService, existing_kit: KitRead, event_bus: EventBus
) -> None:
    completed_events: list[BuildCompleted] = []
    stage_events: list[BuildStageCompleted] = []
    event_bus.subscribe(BuildCompleted, completed_events.append)
    event_bus.subscribe(BuildStageCompleted, stage_events.append)

    build = build_service.create_build(_create_payload(existing_kit))
    stages = build_service.list_stages(build.id)

    for stage in stages:
        build_service.toggle_stage_completion(stage.id, completed=True)

    build = build_service.get_build(build.id)
    assert build.status == "completed"
    assert build.progress_percent == 100
    assert len(stage_events) == len(stages)
    assert len(completed_events) == 1


def test_uncompleting_a_stage_does_not_complete_build(
    build_service: BuildService, existing_kit: KitRead
) -> None:
    build = build_service.create_build(_create_payload(existing_kit))
    stages = build_service.list_stages(build.id)

    build_service.toggle_stage_completion(stages[0].id, completed=True)
    build_service.toggle_stage_completion(stages[0].id, completed=False)

    build = build_service.get_build(build.id)
    assert build.status == "planning"
    assert build.progress_percent == 0


def test_start_pause_resume_build_transitions_status_and_publishes_events(
    build_service: BuildService, existing_kit: KitRead, event_bus: EventBus
) -> None:
    started: list[BuildStarted] = []
    paused: list[BuildPaused] = []
    resumed: list[BuildResumed] = []
    event_bus.subscribe(BuildStarted, started.append)
    event_bus.subscribe(BuildPaused, paused.append)
    event_bus.subscribe(BuildResumed, resumed.append)

    build = build_service.create_build(_create_payload(existing_kit))

    build = build_service.start_build(build.id)
    assert build.status == "in_progress"
    assert build.started_at is not None

    build = build_service.pause_build(build.id)
    assert build.status == "paused"

    build = build_service.resume_build(build.id)
    assert build.status == "in_progress"

    assert len(started) == 1
    assert len(paused) == 1
    assert len(resumed) == 1


def test_mark_completed_sets_status_and_completed_at(
    build_service: BuildService, existing_kit: KitRead
) -> None:
    build = build_service.create_build(_create_payload(existing_kit))

    build = build_service.mark_completed(build.id)

    assert build.status == "completed"
    assert build.completed_at is not None


def test_archive_and_restore_build(build_service: BuildService, existing_kit: KitRead) -> None:
    build = build_service.create_build(_create_payload(existing_kit))

    build_service.archive_build(build.id)
    assert build.id not in [b.id for b in build_service.list_builds()]

    restored = build_service.restore_build(build.id)
    assert restored.is_deleted is False
    assert build.id in [b.id for b in build_service.list_builds()]


def test_progress_override_replaces_computed_progress(
    build_service: BuildService, existing_kit: KitRead
) -> None:
    build = build_service.create_build(_create_payload(existing_kit))

    overridden = build_service.set_progress_override(build.id, 42)
    assert overridden.progress_percent == 42
    assert overridden.is_progress_overridden is True

    cleared = build_service.set_progress_override(build.id, None)
    assert cleared.progress_percent == 0
    assert cleared.is_progress_overridden is False


def test_progress_override_is_clamped_to_0_100(
    build_service: BuildService, existing_kit: KitRead
) -> None:
    build = build_service.create_build(_create_payload(existing_kit))

    build_service.set_progress_override(build.id, 500)
    assert build_service.get_build(build.id).progress_percent == 100

    build_service.set_progress_override(build.id, -50)
    assert build_service.get_build(build.id).progress_percent == 0


def test_operations_on_unknown_build_raise(build_service: BuildService) -> None:
    with pytest.raises(BuildNotFoundError):
        build_service.get_build("missing")
    with pytest.raises(BuildNotFoundError):
        build_service.start_build("missing")
    with pytest.raises(BuildNotFoundError):
        build_service.archive_build("missing")


def test_add_and_remove_stage(build_service: BuildService, existing_kit: KitRead) -> None:
    build = build_service.create_build(_create_payload(existing_kit))
    initial_count = len(build_service.list_stages(build.id))

    new_stage = build_service.add_stage(build.id, "Custom Detailing")
    assert len(build_service.list_stages(build.id)) == initial_count + 1
    assert new_stage.order_index == initial_count

    build_service.remove_stage(new_stage.id)
    assert len(build_service.list_stages(build.id)) == initial_count


def test_move_stage_reorders(build_service: BuildService, existing_kit: KitRead) -> None:
    build = build_service.create_build(_create_payload(existing_kit))
    stages = build_service.list_stages(build.id)
    first_id, second_id = stages[0].id, stages[1].id

    build_service.move_stage(build.id, second_id, direction=-1)

    reordered = build_service.list_stages(build.id)
    assert reordered[0].id == second_id
    assert reordered[1].id == first_id


def test_rename_stage_raises_for_unknown_stage(build_service: BuildService) -> None:
    with pytest.raises(StageNotFoundError):
        build_service.rename_stage("missing", name="x", weight=100)


def test_add_task_and_toggle_completion(build_service: BuildService, existing_kit: KitRead) -> None:
    build = build_service.create_build(_create_payload(existing_kit))
    stage = build_service.list_stages(build.id)[0]

    task = build_service.add_task(stage.id, BuildTaskCreate(title="Wash the runners"))
    assert task.is_completed is False

    completed = build_service.toggle_task_completion(task.id, completed=True)
    assert completed.is_completed is True
    assert completed.completed_at is not None


def test_update_task_details(build_service: BuildService, existing_kit: KitRead) -> None:
    build = build_service.create_build(_create_payload(existing_kit))
    stage = build_service.list_stages(build.id)[0]
    task = build_service.add_task(stage.id, BuildTaskCreate(title="Original"))

    updated = build_service.update_task_details(
        task.id,
        title="Renamed",
        due_date=None,
        estimated_hours=2.5,
        actual_hours=3.0,
        notes="tricky part",
    )

    assert updated.title == "Renamed"
    assert updated.estimated_hours == 2.5
    assert updated.actual_hours == 3.0
    assert updated.notes == "tricky part"


def test_task_operations_on_unknown_task_raise(build_service: BuildService) -> None:
    with pytest.raises(TaskNotFoundError):
        build_service.toggle_task_completion("missing", completed=True)
