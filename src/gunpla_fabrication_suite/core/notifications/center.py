"""A small, in-memory notification history with Qt signal-based delivery.

The UI layer subscribes to :attr:`NotificationCenter.notification_posted`
to render toasts; nothing here depends on Qt widgets, only on
``QtCore.Signal``, so the service stays testable without a running UI.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from PySide6.QtCore import QObject, Signal

from gunpla_fabrication_suite.core.persistence.base import utcnow


class NotificationSeverity(StrEnum):
    """How urgently a notification should be presented."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class Notification:
    """A single, immutable notification."""

    message: str
    severity: NotificationSeverity = NotificationSeverity.INFO
    source: str = "application"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=utcnow)


class NotificationCenter(QObject):
    """Publishes notifications to any listening UI and keeps recent history."""

    notification_posted = Signal(object)

    def __init__(self, *, history_limit: int = 200) -> None:
        super().__init__()
        self._history: list[Notification] = []
        self._history_limit = history_limit

    def post(
        self,
        message: str,
        *,
        severity: NotificationSeverity = NotificationSeverity.INFO,
        source: str = "application",
    ) -> Notification:
        """Create, store, and emit a notification."""
        notification = Notification(message=message, severity=severity, source=source)
        self._history.append(notification)
        if len(self._history) > self._history_limit:
            self._history.pop(0)
        self.notification_posted.emit(notification)
        return notification

    def history(self) -> tuple[Notification, ...]:
        """The most recent notifications, oldest first."""
        return tuple(self._history)
