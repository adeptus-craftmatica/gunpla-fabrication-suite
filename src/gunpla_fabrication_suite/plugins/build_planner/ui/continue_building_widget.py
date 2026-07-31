"""The "Continue Building" dashboard widget: jump back into your most recent build.

"Resume" prepares the shared Build Planner page to show that build (since
the page is a singleton owned by the plugin — see ``plugin.py``) and asks
the shell, via ``Navigator``, to switch to the Build Planner page.
"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget

from gunpla_fabrication_suite.core.navigation import Navigator
from gunpla_fabrication_suite.plugins.build_planner.models.enums import BuildStatus
from gunpla_fabrication_suite.plugins.build_planner.services.build_service import BuildService
from gunpla_fabrication_suite.plugins.build_planner.ui.build_planner_page import BuildPlannerPage
from gunpla_fabrication_suite.plugins.kit_library.services.kit_service import KitService
from gunpla_fabrication_suite.shared_ui import EmptyStateWidget, set_label_role

_PAGE_ID = "build_planner"  # must match plugin.py's NavigationPageContribution(page_id=...)

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
        navigator: Navigator,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)

        builds = [b for b in build_service.list_builds() if b.status in _ACTIVE_STATUSES]
        if not builds:
            layout.addWidget(
                EmptyStateWidget(
                    title="No active builds", description="Start one from the Build Planner."
                )
            )
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
        set_label_role(kit_label, "secondary")
        layout.addWidget(kit_label)

        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(build.progress_percent)
        layout.addWidget(progress_bar)

        resume_button = QPushButton("Resume")
        resume_button.clicked.connect(lambda: self._on_resume(page, navigator, build.id))
        layout.addWidget(resume_button)

    def _on_resume(self, page: BuildPlannerPage, navigator: Navigator, build_id: str) -> None:
        page.show_build(build_id)
        navigator.navigate_to(_PAGE_ID)
