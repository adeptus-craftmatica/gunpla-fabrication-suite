"""The Stats & Insights plugin entry point."""

from __future__ import annotations

from typing import TypeVar

from gunpla_fabrication_suite.plugin_sdk import NavigationPageContribution, PluginContext
from gunpla_fabrication_suite.plugins.build_planner.services.build_service import BuildService
from gunpla_fabrication_suite.plugins.build_planner.services.work_session_service import (
    WorkSessionService,
)
from gunpla_fabrication_suite.plugins.kit_library.services.kit_service import KitService
from gunpla_fabrication_suite.plugins.photography.services.photo_service import PhotoService
from gunpla_fabrication_suite.plugins.stats.services.stats_service import StatsService
from gunpla_fabrication_suite.plugins.stats.ui.stats_page import StatsPage
from gunpla_fabrication_suite.plugins.supplies.services.supply_service import SupplyService

PLUGIN_ID = "com.adeptuscraftmatica.gfs.stats"

T = TypeVar("T")


class StatsPlugin:
    """Rolls up numbers from Kit Library, Build Planner, Supplies, and Photography.

    Resolves those four plugins' services through the shared container
    rather than owning any persistence of its own.
    """

    plugin_id = PLUGIN_ID

    def __init__(self) -> None:
        self._context: PluginContext | None = None
        self._service: StatsService | None = None
        self._page: StatsPage | None = None

    def register(self, context: PluginContext) -> None:
        """Register the Stats & Insights navigation page."""
        self._context = context
        context.navigation.register(
            self.plugin_id,
            NavigationPageContribution(
                page_id="stats",
                title="Stats & Insights",
                factory=self._build_page,
                section="main",
                order=50,
            ),
        )

    def initialize(self) -> None:
        """Resolve every dependency service and build the page once.

        Raises:
            RuntimeError: If any dependency plugin's service was not
                published (all should always be, given the declared
                dependencies).
        """
        if self._context is None:
            raise RuntimeError("initialize() called before register()")

        kit_service = self._require(KitService, "Kit Library")
        build_service = self._require(BuildService, "Build Planner")
        work_session_service = self._require(WorkSessionService, "Build Planner")
        supply_service = self._require(SupplyService, "Supplies")
        photo_service = self._require(PhotoService, "Photography")

        self._service = StatsService(
            kit_service, build_service, work_session_service, supply_service, photo_service
        )
        self._page = StatsPage(self._service)

    def start(self) -> None:
        """No background activity to begin."""

    def stop(self) -> None:
        """No background activity to stop."""

    def shutdown(self) -> None:
        """No resources to release."""

    def _require(self, service_type: type[T], plugin_name: str) -> T:
        assert self._context is not None
        service = self._context.services.try_resolve(service_type)
        if service is None:
            raise RuntimeError(
                f"Stats requires the {plugin_name} plugin's {service_type.__name__}, "
                "which was not found in the service container."
            )
        return service

    def _build_page(self) -> StatsPage:
        assert self._page is not None
        return self._page
