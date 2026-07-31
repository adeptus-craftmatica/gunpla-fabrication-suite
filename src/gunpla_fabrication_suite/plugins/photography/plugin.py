"""The Photography plugin entry point."""

from __future__ import annotations

from gunpla_fabrication_suite.plugin_sdk import (
    DashboardWidgetContribution,
    NavigationPageContribution,
    PluginContext,
)
from gunpla_fabrication_suite.plugins.photography.repositories import PhotoRepository
from gunpla_fabrication_suite.plugins.photography.services import PhotoService
from gunpla_fabrication_suite.plugins.photography.ui.photo_library_page import PhotoLibraryPage
from gunpla_fabrication_suite.plugins.photography.ui.recent_photos_widget import (
    RecentPhotosWidget,
)

PLUGIN_ID = "com.adeptuscraftmatica.gfs.photography"


class PhotographyPlugin:
    """Owns managed photo storage: models, repository, service, and UI.

    Publishes ``PhotoService`` into the shared service container so other
    plugins (e.g. Build Planner) can attach photos to their own entities
    without importing this plugin's repository or ORM models directly.
    """

    plugin_id = PLUGIN_ID

    def __init__(self) -> None:
        self._context: PluginContext | None = None
        self._service: PhotoService | None = None
        self._page: PhotoLibraryPage | None = None

    def register(self, context: PluginContext) -> None:
        """Register the Photo Library navigation page and dashboard widget."""
        self._context = context

        context.navigation.register(
            self.plugin_id,
            NavigationPageContribution(
                page_id="photo_library",
                title="Photo Library",
                factory=self._build_page,
                section="main",
                order=30,
            ),
        )
        context.dashboard_widgets.register(
            self.plugin_id,
            DashboardWidgetContribution(
                widget_id="photography.recent_photos",
                title="Recent Photos",
                factory=self._build_recent_photos_widget,
                order=20,
            ),
        )

    def initialize(self) -> None:
        """Construct the service, the shared library page, and publish the service."""
        if self._context is None:
            raise RuntimeError("initialize() called before register()")

        self._service = PhotoService(
            PhotoRepository(self._context.database), self._context.paths, self._context.events
        )
        self._context.services.register_instance(PhotoService, self._service)

        self._page = PhotoLibraryPage(
            photo_service=self._service,
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

    def _build_page(self) -> PhotoLibraryPage:
        assert self._page is not None
        return self._page

    def _build_recent_photos_widget(self) -> RecentPhotosWidget:
        assert self._service is not None
        return RecentPhotosWidget(self._service)
