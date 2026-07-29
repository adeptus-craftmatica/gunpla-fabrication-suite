"""Repository for :class:`BuildProject`, :class:`BuildStage`, and :class:`BuildTask` rows.

This is the only place in the plugin that issues SQLAlchemy queries against
these three tables; the service layer and UI never do.
"""

from __future__ import annotations

from sqlalchemy import select

from gunpla_fabrication_suite.core.persistence import DatabaseService
from gunpla_fabrication_suite.plugins.build_planner.models.build_project import BuildProject
from gunpla_fabrication_suite.plugins.build_planner.models.build_stage import BuildStage
from gunpla_fabrication_suite.plugins.build_planner.models.build_task import BuildTask


class BuildRepository:
    """CRUD access to build projects, their stages, and their tasks."""

    def __init__(self, database: DatabaseService) -> None:
        self._database = database

    # -- Projects ---------------------------------------------------------

    def add_project(self, project: BuildProject) -> BuildProject:
        """Insert a new build project and return it with generated fields populated."""
        with self._database.session() as session:
            session.add(project)
            session.flush()
            session.refresh(project)
            session.expunge(project)
            return project

    def get_project(self, build_id: str) -> BuildProject | None:
        """Fetch a build project by id, including soft-deleted ones."""
        with self._database.session() as session:
            project = session.get(BuildProject, build_id)
            if project is not None:
                session.expunge(project)
            return project

    def list_projects(self, *, include_archived: bool = False) -> list[BuildProject]:
        """List every build project, most recently updated first."""
        with self._database.session() as session:
            statement = select(BuildProject).order_by(BuildProject.updated_at.desc())
            if not include_archived:
                statement = statement.where(BuildProject.deleted_at.is_(None))
            projects = list(session.scalars(statement))
            for project in projects:
                session.expunge(project)
            return projects

    def update_project(self, project: BuildProject) -> BuildProject:
        """Merge changes to an existing build project back into the database."""
        with self._database.session() as session:
            merged = session.merge(project)
            session.flush()
            session.refresh(merged)
            session.expunge(merged)
            return merged

    # -- Stages -------------------------------------------------------------

    def add_stages(self, stages: list[BuildStage]) -> list[BuildStage]:
        """Insert several stages at once (used when materializing a template)."""
        with self._database.session() as session:
            session.add_all(stages)
            session.flush()
            for stage in stages:
                session.refresh(stage)
                session.expunge(stage)
            return stages

    def add_stage(self, stage: BuildStage) -> BuildStage:
        """Insert a single new stage."""
        return self.add_stages([stage])[0]

    def get_stage(self, stage_id: str) -> BuildStage | None:
        """Fetch a stage by id."""
        with self._database.session() as session:
            stage = session.get(BuildStage, stage_id)
            if stage is not None:
                session.expunge(stage)
            return stage

    def list_stages(self, build_project_id: str) -> list[BuildStage]:
        """List a build's stages, in display order."""
        with self._database.session() as session:
            statement = (
                select(BuildStage)
                .where(BuildStage.build_project_id == build_project_id)
                .order_by(BuildStage.order_index)
            )
            stages = list(session.scalars(statement))
            for stage in stages:
                session.expunge(stage)
            return stages

    def update_stage(self, stage: BuildStage) -> BuildStage:
        """Merge changes to an existing stage back into the database."""
        with self._database.session() as session:
            merged = session.merge(stage)
            session.flush()
            session.refresh(merged)
            session.expunge(merged)
            return merged

    def delete_stage(self, stage_id: str) -> None:
        """Permanently remove a stage (and, via cascade, its tasks)."""
        with self._database.session() as session:
            stage = session.get(BuildStage, stage_id)
            if stage is not None:
                session.delete(stage)

    # -- Tasks ----------------------------------------------------------------

    def add_task(self, task: BuildTask) -> BuildTask:
        """Insert a new task."""
        with self._database.session() as session:
            session.add(task)
            session.flush()
            session.refresh(task)
            session.expunge(task)
            return task

    def get_task(self, task_id: str) -> BuildTask | None:
        """Fetch a task by id."""
        with self._database.session() as session:
            task = session.get(BuildTask, task_id)
            if task is not None:
                session.expunge(task)
            return task

    def list_tasks(self, build_stage_id: str) -> list[BuildTask]:
        """List a stage's tasks, in display order."""
        with self._database.session() as session:
            statement = (
                select(BuildTask)
                .where(BuildTask.build_stage_id == build_stage_id)
                .order_by(BuildTask.order_index)
            )
            tasks = list(session.scalars(statement))
            for task in tasks:
                session.expunge(task)
            return tasks

    def update_task(self, task: BuildTask) -> BuildTask:
        """Merge changes to an existing task back into the database."""
        with self._database.session() as session:
            merged = session.merge(task)
            session.flush()
            session.refresh(merged)
            session.expunge(merged)
            return merged

    def delete_task(self, task_id: str) -> None:
        """Permanently remove a task."""
        with self._database.session() as session:
            task = session.get(BuildTask, task_id)
            if task is not None:
                session.delete(task)
