"""The "Continue Building" dashboard widget: jump back into your most recent build.

"Resume" prepares the shared Build Planner page to show that build (since
the page is a singleton owned by the plugin — see ``plugin.py``) and tells
the user to open Build Planner from the navigation rail. One-click
cross-plugin navigation would need a shell-level "switch to this page" hook
that doesn't exist yet; this is a deliberate, documented scope limit rather
than a half-working button.
"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget

from gunpla_fabrication_suite.core.notifications import NotificationCenter, NotificationSeverity
from gunpla_fabrication_suite.plugins.build_planner.models.enums import BuildStatus
from gunpla_fabrication_suite.plugins.build_planner.services.build_service import BuildService
from gunpla_fabrication_suite.plugins.build_planner.ui.build_planner_page import BuildPlannerPage
from gunpla_fabrication_suite.plugins.kit_library.services.kit_service import KitService
from gunpla_fabrication_suite.shared_ui import EmptyStateWidget
from gunpla_fabrication_suite.themes import PALETTE

_ACTIVE_STATUSES = frozenset(
    {
        BuildStatus.PLANNING.value,
        BuildStatus.IN_PROGRESS.value,
        BuildStatus.PAUSED.value,
        BuildStatus.WAITING_ON_SUPPLIES.value,
        BuildStatus.WAITING_ON_REPLACEMENT_PARTS.value,
    }
)


class ContinueBuildingWidget(QWidget):
    """Surfaces the most recently updated active build with a one-click resume."""

    def __init__(
        self,
        build_service: BuildService,
        kit_service: KitService,
        page: BuildPlannerPage,
        notifications: NotificationCenter,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)

        builds = [b for b in build_service.list_builds() if b.status in _ACTIVE_STATUSES]
        if not builds:
            # Deliberately no description text here: this card's height is
            # capped to its sizeHint (see dashboard_page.py's card sizing),
            # and a wrapped second line can be clipped before the grid
            # layout settles on a final column width. Keeping dashboard-card
            # empty states to a single, short line sidesteps that entirely.
            layout.addWidget(EmptyStateWidget(title="No active builds"))
            return

        build = builds[0]  # list_builds() already orders by most recently updated

        title_label = QLabel(build.title)
        title_label.setStyleSheet("font-weight: 600;")
        layout.addWidget(title_label)

        try:
            kit = kit_service.get_kit(build.kit_id)
            kit_label = QLabel(f"{kit.manufacturer} — {kit.name}")
        except Exception:
            kit_label = QLabel("Kit unavailable")
        kit_label.setStyleSheet(f"color: {PALETTE.text_secondary};")
        layout.addWidget(kit_label)

        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(build.progress_percent)
        layout.addWidget(progress_bar)

        resume_button = QPushButton("Resume")
        resume_button.clicked.connect(
            lambda: self._on_resume(page, notifications, build.id, build.title)
        )
        layout.addWidget(resume_button)

    def _on_resume(
        self, page: BuildPlannerPage, notifications: NotificationCenter, build_id: str, title: str
    ) -> None:
        page.show_build(build_id)
        notifications.post(
            f"Opened '{title}' — select Build Planner in the navigation to continue.",
            severity=NotificationSeverity.INFO,
            source="build_planner",
        )
