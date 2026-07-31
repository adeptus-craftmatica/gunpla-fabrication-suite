"""The Build Planner page: switches between the build list and a build's detail view."""

from __future__ import annotations

from PySide6.QtWidgets import QStackedLayout, QWidget

from gunpla_fabrication_suite.core.jobs import BackgroundJobManager
from gunpla_fabrication_suite.core.layout import LayoutManager
from gunpla_fabrication_suite.core.notifications import NotificationCenter
from gunpla_fabrication_suite.plugins.build_planner.services.build_service import BuildService
from gunpla_fabrication_suite.plugins.build_planner.services.journal_service import JournalService
from gunpla_fabrication_suite.plugins.build_planner.services.work_session_service import (
    WorkSessionService,
)
from gunpla_fabrication_suite.plugins.build_planner.ui.build_detail_view import BuildDetailView
from gunpla_fabrication_suite.plugins.build_planner.ui.build_list_view import BuildListView
from gunpla_fabrication_suite.plugins.kit_library.services.kit_service import KitService
from gunpla_fabrication_suite.plugins.photography.services.photo_service import PhotoService


class BuildPlannerPage(QWidget):
    """Owns the list<->detail navigation within the Build Planner nav entry.

    A fresh :class:`BuildDetailView` is created per selected build (and torn
    down, including its live timer, when leaving it) rather than kept around
    indefinitely — builds are usually visited one at a time.
    """

    def __init__(
        self,
        *,
        build_service: BuildService,
        work_session_service: WorkSessionService,
        journal_service: JournalService,
        kit_service: KitService,
        photo_service: PhotoService,
        jobs: BackgroundJobManager,
        notifications: NotificationCenter,
        layout_manager: LayoutManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._build_service = build_service
        self._work_session_service = work_session_service
        self._journal_service = journal_service
        self._kit_service = kit_service
        self._photo_service = photo_service
        self._jobs = jobs
        self._notifications = notifications
        self._layout_manager = layout_manager

        self._stack = QStackedLayout(self)
        self._detail_view: BuildDetailView | None = None

        self._list_view = BuildListView(
            build_service, kit_service, layout_manager, on_select=self.show_build
        )
        self._stack.addWidget(self._list_view)

    def show_build(self, build_id: str) -> None:
        """Show the detail view for ``build_id``, replacing any previous detail view."""
        self._teardown_detail_view()

        self._detail_view = BuildDetailView(
            build_service=self._build_service,
            work_session_service=self._work_session_service,
            journal_service=self._journal_service,
            kit_service=self._kit_service,
            photo_service=self._photo_service,
            jobs=self._jobs,
            notifications=self._notifications,
            layout_manager=self._layout_manager,
            build_id=build_id,
            on_back=self.show_list,
        )
        self._stack.addWidget(self._detail_view)
        self._stack.setCurrentWidget(self._detail_view)

    def show_list(self) -> None:
        """Return to the build list, refreshing it and tearing down any detail view."""
        self._stack.setCurrentWidget(self._list_view)
        self._list_view.refresh()
        self._teardown_detail_view()

    def _teardown_detail_view(self) -> None:
        if self._detail_view is not None:
            self._stack.removeWidget(self._detail_view)
            self._detail_view.setParent(None)
            self._detail_view.deleteLater()
            self._detail_view = None
