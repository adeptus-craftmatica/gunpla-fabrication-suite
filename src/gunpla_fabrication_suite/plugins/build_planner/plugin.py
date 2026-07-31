"""The Build Planner plugin entry point."""

from __future__ import annotations

from gunpla_fabrication_suite.plugin_sdk import (
    DashboardWidgetContribution,
    NavigationPageContribution,
    PluginContext,
)
from gunpla_fabrication_suite.plugins.build_planner.repositories.build_repository import (
    BuildRepository,
)
from gunpla_fabrication_suite.plugins.build_planner.repositories.journal_repository import (
    JournalRepository,
)
from gunpla_fabrication_suite.plugins.build_planner.repositories.supply_usage_repository import (
    SupplyUsageRepository,
)
from gunpla_fabrication_suite.plugins.build_planner.repositories.work_session_repository import (
    WorkSessionRepository,
)
from gunpla_fabrication_suite.plugins.build_planner.services.build_service import BuildService
from gunpla_fabrication_suite.plugins.build_planner.services.journal_service import JournalService
from gunpla_fabrication_suite.plugins.build_planner.services.supply_usage_service import (
    SupplyUsageService,
)
from gunpla_fabrication_suite.plugins.build_planner.services.work_session_service import (
    WorkSessionService,
)
from gunpla_fabrication_suite.plugins.build_planner.ui.build_planner_page import BuildPlannerPage
from gunpla_fabrication_suite.plugins.build_planner.ui.continue_building_widget import (
    ContinueBuildingWidget,
)
from gunpla_fabrication_suite.plugins.kit_library.services.kit_service import KitService
from gunpla_fabrication_suite.plugins.photography.services.photo_service import PhotoService
from gunpla_fabrication_suite.plugins.supplies.services.supply_service import SupplyService

PLUGIN_ID = "com.adeptuscraftmatica.gfs.build_planner"


class BuildPlannerPlugin:
    """Owns build tracking: models, repositories, services, and UI.

    Depends on Kit Library, Photography, and Supplies, and resolves their
    ``KitService``, ``PhotoService``, and ``SupplyService`` through the
    shared service container (see ``manifest.toml``'s ``dependencies``,
    which guarantees all three have already registered those services by
    the time this plugin's ``initialize()`` runs).
    """

    plugin_id = PLUGIN_ID

    def __init__(self) -> None:
        self._context: PluginContext | None = None
        self._build_service: BuildService | None = None
        self._work_session_service: WorkSessionService | None = None
        self._journal_service: JournalService | None = None
        self._supply_usage_service: SupplyUsageService | None = None
        self._kit_service: KitService | None = None
        self._photo_service: PhotoService | None = None
        self._supply_service: SupplyService | None = None
        self._page: BuildPlannerPage | None = None

    def register(self, context: PluginContext) -> None:
        """Register the Build Planner navigation page and dashboard widget."""
        self._context = context

        context.navigation.register(
            self.plugin_id,
            NavigationPageContribution(
                page_id="build_planner",
                title="Build Planner",
                factory=self._build_page,
                section="main",
                order=20,
                focus=lambda build_id: self._page.show_build(build_id) if self._page else None,
            ),
        )
        context.dashboard_widgets.register(
            self.plugin_id,
            DashboardWidgetContribution(
                widget_id="build_planner.continue_building",
                title="Continue Building",
                factory=self._build_continue_widget,
                order=0,
            ),
        )

    def initialize(self) -> None:
        """Construct services and the shared Build Planner page.

        Raises:
            RuntimeError: If Kit Library's ``KitService``, Photography's
                ``PhotoService``, or Supplies' ``SupplyService`` was not
                published (all three should always be, given the declared
                dependencies).
        """
        if self._context is None:
            raise RuntimeError("initialize() called before register()")

        kit_service = self._context.services.try_resolve(KitService)
        if kit_service is None:
            raise RuntimeError(
                "Build Planner requires the Kit Library plugin's KitService, "
                "which was not found in the service container."
            )
        self._kit_service = kit_service

        photo_service = self._context.services.try_resolve(PhotoService)
        if photo_service is None:
            raise RuntimeError(
                "Build Planner requires the Photography plugin's PhotoService, "
                "which was not found in the service container."
            )
        self._photo_service = photo_service

        supply_service = self._context.services.try_resolve(SupplyService)
        if supply_service is None:
            raise RuntimeError(
                "Build Planner requires the Supplies plugin's SupplyService, "
                "which was not found in the service container."
            )
        self._supply_service = supply_service

        self._build_service = BuildService(
            BuildRepository(self._context.database), kit_service, self._context.events
        )
        self._work_session_service = WorkSessionService(
            WorkSessionRepository(self._context.database), self._context.events
        )
        self._journal_service = JournalService(JournalRepository(self._context.database))
        self._supply_usage_service = SupplyUsageService(
            SupplyUsageRepository(self._context.database), supply_service, self._context.events
        )

        # Published so other plugins (e.g. Stats, Global Search) can resolve
        # build data through the shared container without importing this
        # plugin's repositories or ORM models — same pattern Kit Library,
        # Photography, and Supplies already use for their own services.
        # JournalService is intentionally not published — nothing needs it.
        self._context.services.register_instance(BuildService, self._build_service)
        self._context.services.register_instance(WorkSessionService, self._work_session_service)
        self._context.services.register_instance(SupplyUsageService, self._supply_usage_service)

        self._page = BuildPlannerPage(
            build_service=self._build_service,
            work_session_service=self._work_session_service,
            journal_service=self._journal_service,
            supply_usage_service=self._supply_usage_service,
            kit_service=kit_service,
            photo_service=photo_service,
            supply_service=supply_service,
            jobs=self._context.jobs,
            notifications=self._context.notifications,
            layout_manager=self._context.layout_manager,
        )

    def start(self) -> None:
        """No background activity to begin."""

    def stop(self) -> None:
        """No background activity to stop."""

    def shutdown(self) -> None:
        """No resources to release."""

    def _build_page(self) -> BuildPlannerPage:
        assert self._page is not None
        return self._page

    def _build_continue_widget(self) -> ContinueBuildingWidget:
        assert (
            self._build_service is not None
            and self._kit_service is not None
            and self._page is not None
            and self._context is not None
        )
        return ContinueBuildingWidget(
            self._build_service, self._kit_service, self._page, self._context.navigator
        )
