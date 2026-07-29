"""Runs long-running work off the Qt UI thread and reports progress.

Any plugin task that touches the network or does non-trivial image
processing must go through :class:`BackgroundJobManager` instead of running
directly on a signal handler or button click, so the UI thread never blocks.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from gunpla_fabrication_suite.core.logging import get_logger
from gunpla_fabrication_suite.core.persistence.base import utcnow

_logger = get_logger("jobs")

ProgressReporter = Callable[[int, str], None]
JobFunction = Callable[[ProgressReporter], Any]


class JobStatus(StrEnum):
    """The lifecycle state of a background job."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class JobRecord:
    """Metadata describing a background job's current state."""

    id: str
    name: str
    status: JobStatus = JobStatus.QUEUED
    progress_percent: int = 0
    progress_message: str = ""
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class _JobSignals(QObject):
    progress = Signal(str, int, str)
    finished = Signal(str, object)
    failed = Signal(str, str)


class _JobRunnable(QRunnable):
    def __init__(self, job_id: str, func: JobFunction, cancel_flag: list[bool]) -> None:
        super().__init__()
        self.signals = _JobSignals()
        self._job_id = job_id
        self._func = func
        self._cancel_flag = cancel_flag

    @Slot()
    def run(self) -> None:
        def report_progress(percent: int, message: str) -> None:
            self.signals.progress.emit(self._job_id, percent, message)

        try:
            result = self._func(report_progress)
        except Exception as exc:
            _logger.exception("background_job_failed", job_id=self._job_id)
            self.signals.failed.emit(self._job_id, str(exc))
        else:
            self.signals.finished.emit(self._job_id, result)


class JobHandle:
    """A handle to a submitted job, exposing its live status via Qt signals."""

    def __init__(self, record: JobRecord, cancel_flag: list[bool]) -> None:
        self._record = record
        self._cancel_flag = cancel_flag

    @property
    def id(self) -> str:
        """The job's unique identifier."""
        return self._record.id

    @property
    def record(self) -> JobRecord:
        """The job's current metadata snapshot."""
        return self._record

    def cancel(self) -> None:
        """Request cooperative cancellation.

        The job function must periodically check for cancellation itself;
        this only sets a flag it can observe.
        """
        self._cancel_flag[0] = True

    def is_cancel_requested(self) -> bool:
        """Whether :meth:`cancel` has been called for this job."""
        return self._cancel_flag[0]


class BackgroundJobManager(QObject):
    """Submits work to a Qt thread pool and reports progress back to the UI thread."""

    job_progress = Signal(str, int, str)
    job_succeeded = Signal(str, object)
    job_failed = Signal(str, str)

    def __init__(self, *, max_thread_count: int | None = None) -> None:
        super().__init__()
        self._pool = QThreadPool()
        if max_thread_count is not None:
            self._pool.setMaxThreadCount(max_thread_count)
        self._jobs: dict[str, JobHandle] = {}

    def submit(self, name: str, func: JobFunction) -> JobHandle:
        """Queue ``func`` to run on a worker thread and return its handle.

        ``func`` receives a ``report_progress(percent, message)`` callable.
        """
        job_id = str(uuid.uuid4())
        record = JobRecord(id=job_id, name=name)
        cancel_flag = [False]
        handle = JobHandle(record, cancel_flag)
        self._jobs[job_id] = handle

        runnable = _JobRunnable(job_id, func, cancel_flag)
        runnable.signals.progress.connect(self._on_progress)
        runnable.signals.finished.connect(self._on_finished)
        runnable.signals.failed.connect(self._on_failed)

        record.status = JobStatus.RUNNING
        record.started_at = utcnow()
        self._pool.start(runnable)
        return handle

    def _on_progress(self, job_id: str, percent: int, message: str) -> None:
        handle = self._jobs.get(job_id)
        if handle is None:
            return
        handle.record.progress_percent = percent
        handle.record.progress_message = message
        self.job_progress.emit(job_id, percent, message)

    def _on_finished(self, job_id: str, result: object) -> None:
        handle = self._jobs.get(job_id)
        if handle is None:
            return
        handle.record.status = JobStatus.SUCCEEDED
        handle.record.completed_at = utcnow()
        self.job_succeeded.emit(job_id, result)

    def _on_failed(self, job_id: str, error: str) -> None:
        handle = self._jobs.get(job_id)
        if handle is None:
            return
        handle.record.status = JobStatus.FAILED
        handle.record.error = error
        handle.record.completed_at = utcnow()
        self.job_failed.emit(job_id, error)

    def active_jobs(self) -> tuple[JobRecord, ...]:
        """Snapshot of every job this manager has ever tracked, in insertion order."""
        return tuple(handle.record for handle in self._jobs.values())
