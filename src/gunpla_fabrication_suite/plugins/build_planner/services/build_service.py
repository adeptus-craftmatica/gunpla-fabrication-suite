"""Business logic for build projects, their stages, and their tasks.

Progress is computed as a weighted percentage of completed stages unless a
manual override is active, matching the "show the score breakdown
transparently, never a silent number" spirit used elsewhere in this app.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from gunpla_fabrication_suite.core.events import EventBus
from gunpla_fabrication_suite.plugins.build_planner.errors import (
    BuildNotFoundError,
    StageNotFoundError,
    TaskNotFoundError,
)
from gunpla_fabrication_suite.plugins.build_planner.events import (
    BuildCompleted,
    BuildCreated,
    BuildPaused,
    BuildResumed,
    BuildStageCompleted,
    BuildStarted,
)
from gunpla_fabrication_suite.plugins.build_planner.models.build_project import BuildProject
from gunpla_fabrication_suite.plugins.build_planner.models.build_stage import BuildStage
from gunpla_fabrication_suite.plugins.build_planner.models.build_task import BuildTask
from gunpla_fabrication_suite.plugins.build_planner.models.enums import BuildStatus
from gunpla_fabrication_suite.plugins.build_planner.repositories.build_repository import (
    BuildRepository,
)
from gunpla_fabrication_suite.plugins.build_planner.schemas import (
    BuildProjectCreate,
    BuildProjectRead,
    BuildStageRead,
    BuildTaskCreate,
    BuildTaskRead,
)
from gunpla_fabrication_suite.plugins.build_planner.templates import get_template
from gunpla_fabrication_suite.plugins.kit_library.services.kit_service import KitService


class BuildService:
    """Creates builds from templates, tracks stage/task progress, and manages status."""

    def __init__(
        self, repository: BuildRepository, kit_service: KitService, events: EventBus
    ) -> None:
        self._repository = repository
        self._kit_service = kit_service
        self._events = events

    def create_build(self, data: BuildProjectCreate) -> BuildProjectRead:
        """Start a new build from a kit and a template.

        Raises:
            gunpla_fabrication_suite.plugins.kit_library.services.kit_service.KitNotFoundError:
                If ``data.kit_id`` does not exist.
            UnknownTemplateError: If ``data.template_key`` is not registered.
        """
        self._kit_service.get_kit(data.kit_id)  # raises KitNotFoundError if missing
        template = get_template(data.template_key)

        project = BuildProject(
            kit_id=data.kit_id,
            title=data.title,
            template_key=data.template_key,
            status=BuildStatus.PLANNING.value,
            is_commission=data.is_commission,
        )
        saved = self._repository.add_project(project)

        stages = [
            BuildStage(build_project_id=saved.id, name=name, order_index=index, weight=100)
            for index, name in enumerate(template.stage_names)
        ]
        self._repository.add_stages(stages)

        self._events.publish(
            BuildCreated(
                build_id=saved.id,
                kit_id=saved.kit_id,
                title=saved.title,
                created_at=saved.created_at,
            )
        )
        return self._to_read(saved)

    def get_build(self, build_id: str) -> BuildProjectRead:
        """Fetch a single build with its computed progress.

        Raises:
            BuildNotFoundError: If ``build_id`` does not exist.
        """
        project = self._require_project(build_id)
        return self._to_read(project)

    def list_builds(self, *, include_archived: bool = False) -> list[BuildProjectRead]:
        """List builds, excluding archived ones by default."""
        projects = self._repository.list_projects(include_archived=include_archived)
        return [self._to_read(project) for project in projects]

    def update_details(self, build_id: str, *, title: str, notes: str | None) -> BuildProjectRead:
        """Rename a build and/or change its free-text notes.

        Raises:
            BuildNotFoundError: If ``build_id`` does not exist.
        """
        project = self._require_project(build_id)
        project.title = title
        project.notes = notes
        project.version += 1
        saved = self._repository.update_project(project)
        return self._to_read(saved)

    def start_build(self, build_id: str) -> BuildProjectRead:
        """Move a build from Planning into active work.

        Raises:
            BuildNotFoundError: If ``build_id`` does not exist.
        """
        project = self._require_project(build_id)
        project.status = BuildStatus.IN_PROGRESS.value
        if project.started_at is None:
            project.started_at = datetime.now(UTC)
        started_at = project.started_at
        saved = self._repository.update_project(project)
        self._events.publish(BuildStarted(build_id=saved.id, started_at=started_at))
        return self._to_read(saved)

    def pause_build(self, build_id: str) -> BuildProjectRead:
        """Pause an in-progress build.

        Raises:
            BuildNotFoundError: If ``build_id`` does not exist.
        """
        project = self._require_project(build_id)
        project.status = BuildStatus.PAUSED.value
        saved = self._repository.update_project(project)
        self._events.publish(BuildPaused(build_id=saved.id))
        return self._to_read(saved)

    def resume_build(self, build_id: str) -> BuildProjectRead:
        """Resume a paused build.

        Raises:
            BuildNotFoundError: If ``build_id`` does not exist.
        """
        project = self._require_project(build_id)
        project.status = BuildStatus.IN_PROGRESS.value
        saved = self._repository.update_project(project)
        self._events.publish(BuildResumed(build_id=saved.id))
        return self._to_read(saved)

    def mark_completed(self, build_id: str) -> BuildProjectRead:
        """Explicitly mark a build completed, regardless of stage progress.

        Raises:
            BuildNotFoundError: If ``build_id`` does not exist.
        """
        project = self._require_project(build_id)
        return self._complete(project)

    def archive_build(self, build_id: str) -> None:
        """Soft-delete a build.

        Raises:
            BuildNotFoundError: If ``build_id`` does not exist.
        """
        project = self._require_project(build_id)
        project.deleted_at = datetime.now(UTC)
        self._repository.update_project(project)

    def restore_build(self, build_id: str) -> BuildProjectRead:
        """Clear a build's soft-deletion.

        Raises:
            BuildNotFoundError: If ``build_id`` does not exist.
        """
        project = self._require_project(build_id)
        project.deleted_at = None
        saved = self._repository.update_project(project)
        return self._to_read(saved)

    def set_progress_override(self, build_id: str, percent: int | None) -> BuildProjectRead:
        """Set or clear a manual progress override.

        Raises:
            BuildNotFoundError: If ``build_id`` does not exist.
        """
        project = self._require_project(build_id)
        project.progress_override_percent = None if percent is None else max(0, min(100, percent))
        saved = self._repository.update_project(project)
        return self._to_read(saved)

    # -- Stages ---------------------------------------------------------------

    def list_stages(self, build_id: str) -> list[BuildStageRead]:
        """List a build's stages in display order."""
        stages = self._repository.list_stages(build_id)
        return [BuildStageRead.model_validate(stage) for stage in stages]

    def add_stage(self, build_id: str, name: str, *, weight: int = 100) -> BuildStageRead:
        """Append a new stage to the end of a build's stage list."""
        existing = self._repository.list_stages(build_id)
        stage = BuildStage(
            build_project_id=build_id, name=name, order_index=len(existing), weight=weight
        )
        saved = self._repository.add_stage(stage)
        return BuildStageRead.model_validate(saved)

    def reorder_stages(self, build_id: str, ordered_stage_ids: list[str]) -> list[BuildStageRead]:
        """Reassign stage order to match ``ordered_stage_ids``."""
        stages_by_id = {stage.id: stage for stage in self._repository.list_stages(build_id)}
        for index, stage_id in enumerate(ordered_stage_ids):
            stage = stages_by_id.get(stage_id)
            if stage is not None:
                stage.order_index = index
                self._repository.update_stage(stage)
        return self.list_stages(build_id)

    def remove_stage(self, stage_id: str) -> None:
        """Permanently remove a stage and its tasks."""
        self._repository.delete_stage(stage_id)

    def rename_stage(self, stage_id: str, *, name: str, weight: int) -> BuildStageRead:
        """Change a stage's name and/or progress weight.

        Raises:
            StageNotFoundError: If ``stage_id`` does not exist.
        """
        stage = self._repository.get_stage(stage_id)
        if stage is None:
            raise StageNotFoundError(stage_id)
        stage.name = name
        stage.weight = weight
        saved = self._repository.update_stage(stage)
        return BuildStageRead.model_validate(saved)

    def move_stage(self, build_id: str, stage_id: str, *, direction: int) -> list[BuildStageRead]:
        """Move a stage one position earlier (``direction=-1``) or later (``+1``)."""
        stages = sorted(self._repository.list_stages(build_id), key=lambda s: s.order_index)
        index = next((i for i, s in enumerate(stages) if s.id == stage_id), None)
        target = None if index is None else index + direction
        if index is not None and target is not None and 0 <= target < len(stages):
            stages[index], stages[target] = stages[target], stages[index]
            for order, stage in enumerate(stages):
                stage.order_index = order
                self._repository.update_stage(stage)
        return self.list_stages(build_id)

    def toggle_stage_completion(self, stage_id: str, *, completed: bool) -> BuildStageRead:
        """Mark a stage complete or incomplete.

        If every stage in the build is now complete, the build itself is
        automatically marked completed.

        Raises:
            StageNotFoundError: If ``stage_id`` does not exist.
        """
        stage = self._repository.get_stage(stage_id)
        if stage is None:
            raise StageNotFoundError(stage_id)

        completed_at = datetime.now(UTC) if completed else None
        stage.is_completed = completed
        stage.completed_at = completed_at
        saved = self._repository.update_stage(stage)

        if completed and completed_at is not None:
            self._events.publish(
                BuildStageCompleted(
                    build_id=saved.build_project_id,
                    stage_id=saved.id,
                    completed_at=completed_at,
                )
            )
            all_stages = self._repository.list_stages(saved.build_project_id)
            if all_stages and all(s.is_completed for s in all_stages):
                project = self._repository.get_project(saved.build_project_id)
                if project is not None and project.status != BuildStatus.COMPLETED.value:
                    self._complete(project)

        return BuildStageRead.model_validate(saved)

    # -- Tasks ------------------------------------------------------------------

    def list_tasks(self, stage_id: str) -> list[BuildTaskRead]:
        """List a stage's tasks in display order."""
        tasks = self._repository.list_tasks(stage_id)
        return [BuildTaskRead.model_validate(task) for task in tasks]

    def add_task(self, stage_id: str, data: BuildTaskCreate) -> BuildTaskRead:
        """Add a new task to a stage."""
        existing = self._repository.list_tasks(stage_id)
        task = BuildTask(
            build_stage_id=stage_id,
            title=data.title,
            order_index=len(existing),
            due_date=data.due_date,
            estimated_hours=data.estimated_hours,
            notes=data.notes,
        )
        saved = self._repository.add_task(task)
        return BuildTaskRead.model_validate(saved)

    def toggle_task_completion(self, task_id: str, *, completed: bool) -> BuildTaskRead:
        """Mark a task complete or incomplete.

        Raises:
            TaskNotFoundError: If ``task_id`` does not exist.
        """
        task = self._require_task(task_id)
        task.is_completed = completed
        task.completed_at = datetime.now(UTC) if completed else None
        saved = self._repository.update_task(task)
        return BuildTaskRead.model_validate(saved)

    def update_task_details(
        self,
        task_id: str,
        *,
        title: str,
        due_date: date | None,
        estimated_hours: float | None,
        actual_hours: float | None,
        notes: str | None,
    ) -> BuildTaskRead:
        """Update a task's editable fields.

        Raises:
            TaskNotFoundError: If ``task_id`` does not exist.
        """
        task = self._require_task(task_id)
        task.title = title
        task.due_date = due_date
        task.estimated_hours = estimated_hours
        task.actual_hours = actual_hours
        task.notes = notes
        saved = self._repository.update_task(task)
        return BuildTaskRead.model_validate(saved)

    def remove_task(self, task_id: str) -> None:
        """Permanently remove a task."""
        self._repository.delete_task(task_id)

    # -- Internal helpers ---------------------------------------------------------

    def compute_progress_percent(self, build_id: str) -> int:
        """The weighted percentage of a build's stages that are complete."""
        stages = self._repository.list_stages(build_id)
        if not stages:
            return 0
        total_weight = sum(stage.weight for stage in stages)
        if total_weight <= 0:
            return 0
        completed_weight = sum(stage.weight for stage in stages if stage.is_completed)
        return round(completed_weight / total_weight * 100)

    def _complete(self, project: BuildProject) -> BuildProjectRead:
        completed_at = datetime.now(UTC)
        project.status = BuildStatus.COMPLETED.value
        project.completed_at = completed_at
        saved = self._repository.update_project(project)
        self._events.publish(BuildCompleted(build_id=saved.id, completed_at=completed_at))
        return self._to_read(saved)

    def _require_project(self, build_id: str) -> BuildProject:
        project = self._repository.get_project(build_id)
        if project is None:
            raise BuildNotFoundError(build_id)
        return project

    def _require_task(self, task_id: str) -> BuildTask:
        task = self._repository.get_task(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        return task

    def _to_read(self, project: BuildProject) -> BuildProjectRead:
        progress = (
            project.progress_override_percent
            if project.progress_override_percent is not None
            else self.compute_progress_percent(project.id)
        )
        return BuildProjectRead(
            id=project.id,
            kit_id=project.kit_id,
            title=project.title,
            template_key=project.template_key,
            status=project.status,
            is_commission=project.is_commission,
            progress_override_percent=project.progress_override_percent,
            is_progress_overridden=project.is_progress_overridden,
            progress_percent=progress,
            started_at=project.started_at,
            completed_at=project.completed_at,
            notes=project.notes,
            is_deleted=project.is_deleted,
            version=project.version,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )
