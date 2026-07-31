"""The Kit Library plugin entry point."""

from __future__ import annotations

from gunpla_fabrication_suite.plugin_sdk import (
    DashboardWidgetContribution,
    NavigationPageContribution,
    PluginContext,
)
from gunpla_fabrication_suite.plugins.kit_library.repositories.kit_repository import KitRepository
from gunpla_fabrication_suite.plugins.kit_library.services.kit_service import KitService
from gunpla_fabrication_suite.plugins.kit_library.ui.backlog_widget import BacklogCountWidget
from gunpla_fabrication_suite.plugins.kit_library.ui.kit_library_page import KitLibraryPage

PLUGIN_ID = "com.adeptuscraftmatica.gfs.kit_library"


class KitLibraryPlugin:
    """Owns kit collection and backlog data: models, repository, service, and UI."""

    plugin_id = PLUGIN_ID

    def __init__(self) -> None:
        self._context: PluginContext | None = None
        self._service: KitService | None = None

    def register(self, context: PluginContext) -> None:
        """Register the Kit Library navigation page and its dashboard widget."""
        self._context = context

        context.navigation.register(
            self.plugin_id,
            NavigationPageContribution(
                page_id="kit_library",
                title="Kit Library",
                factory=self._build_page,
                section="main",
                order=10,
            ),
        )
        context.dashboard_widgets.register(
            self.plugin_id,
            DashboardWidgetContribution(
                widget_id="kit_library.backlog_count",
                title="Active Kits",
                factory=self._build_backlog_widget,
                order=10,
            ),
        )

    def initialize(self) -> None:
        """Construct the repository and service, and publish the service for other plugins.

        Other plugins (e.g. Build Planner) depend on Kit Library and resolve
        ``KitService`` through the shared service container rather than
        importing this plugin's repository or ORM models directly.
        """
        if self._context is None:
            raise RuntimeError("initialize() called before register()")
        repository = KitRepository(self._context.database)
        self._service = KitService(repository, self._context.events)
        self._context.services.register_instance(KitService, self._service)

    def start(self) -> None:
        """No background activity to begin."""

    def stop(self) -> None:
        """No background activity to stop."""

    def shutdown(self) -> None:
        """No resources to release."""

    def _build_page(self) -> KitLibraryPage:
        assert self._service is not None and self._context is not None
        return KitLibraryPage(
            self._service,
            self._context.notifications,
            self._context.layout_manager,
            self._context.inspector,
        )

    def _build_backlog_widget(self) -> BacklogCountWidget:
        assert self._service is not None
        return BacklogCountWidget(self._service)
