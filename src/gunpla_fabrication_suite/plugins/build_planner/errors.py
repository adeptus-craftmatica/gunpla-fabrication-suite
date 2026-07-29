"""Exceptions raised by Build Planner services."""

from __future__ import annotations


class BuildNotFoundError(LookupError):
    """Raised when an operation targets a build id that does not exist."""

    def __init__(self, build_id: str) -> None:
        super().__init__(f"No build found with id {build_id!r}")
        self.build_id = build_id


class StageNotFoundError(LookupError):
    """Raised when an operation targets a stage id that does not exist."""

    def __init__(self, stage_id: str) -> None:
        super().__init__(f"No stage found with id {stage_id!r}")
        self.stage_id = stage_id


class TaskNotFoundError(LookupError):
    """Raised when an operation targets a task id that does not exist."""

    def __init__(self, task_id: str) -> None:
        super().__init__(f"No task found with id {task_id!r}")
        self.task_id = task_id


class WorkSessionNotFoundError(LookupError):
    """Raised when an operation targets a work session id that does not exist."""

    def __init__(self, session_id: str) -> None:
        super().__init__(f"No work session found with id {session_id!r}")
        self.session_id = session_id


class WorkSessionAlreadyRunningError(RuntimeError):
    """Raised when starting a timer while another one is already running."""

    def __init__(self, build_id: str) -> None:
        super().__init__(f"A work session is already running for build {build_id!r}")
        self.build_id = build_id


class UnknownTemplateError(LookupError):
    """Raised when a build is created with a template key that does not exist."""

    def __init__(self, template_key: str) -> None:
        super().__init__(f"No build template registered under {template_key!r}")
        self.template_key = template_key
