"""The Wishlist plugin entry point."""

from __future__ import annotations

from gunpla_fabrication_suite.plugin_sdk import (
    DashboardWidgetContribution,
    NavigationPageContribution,
    PluginContext,
)
from gunpla_fabrication_suite.plugins.kit_library.services.kit_service import KitService
from gunpla_fabrication_suite.plugins.wishlist.repositories.wishlist_repository import (
    WishlistRepository,
)
from gunpla_fabrication_suite.plugins.wishlist.services.wishlist_service import WishlistService
from gunpla_fabrication_suite.plugins.wishlist.ui.wishlist_page import WishlistPage
from gunpla_fabrication_suite.plugins.wishlist.ui.wishlist_widget import WishlistCountWidget

PLUGIN_ID = "com.adeptuscraftmatica.gfs.wishlist"


class WishlistPlugin:
    """Owns wishlist data: models, repository, service, and UI.

    Depends on Kit Library's ``KitService`` so that marking a kit-type item
    purchased can create a real Kit Library entry — the same
    resolve-in-``initialize()`` pattern Build Planner uses for both Kit
    Library and Supplies.
    """

    plugin_id = PLUGIN_ID

    def __init__(self) -> None:
        self._context: PluginContext | None = None
        self._service: WishlistService | None = None
        self._page: WishlistPage | None = None

    def register(self, context: PluginContext) -> None:
        """Register the Wishlist navigation page and its dashboard widget."""
        self._context = context

        context.navigation.register(
            self.plugin_id,
            NavigationPageContribution(
                page_id="wishlist",
                title="Wishlist",
                factory=self._build_page,
                section="main",
                order=60,
                focus=lambda item_id: self._page.show_item(item_id) if self._page else None,
            ),
        )
        context.dashboard_widgets.register(
            self.plugin_id,
            DashboardWidgetContribution(
                widget_id="wishlist.item_count",
                title="Wishlist",
                factory=self._build_widget,
                order=45,
            ),
        )

    def initialize(self) -> None:
        """Construct the repository and service, and publish the service for other plugins.

        Raises:
            RuntimeError: If Kit Library's ``KitService`` was not published —
                shouldn't happen given the declared manifest dependency.
        """
        if self._context is None:
            raise RuntimeError("initialize() called before register()")

        kit_service = self._context.services.try_resolve(KitService)
        if kit_service is None:
            raise RuntimeError(
                "Wishlist requires the Kit Library plugin's KitService, "
                "which was not found in the service container."
            )

        repository = WishlistRepository(self._context.database)
        self._service = WishlistService(repository, self._context.events)
        self._context.services.register_instance(WishlistService, self._service)
        self._page = WishlistPage(
            self._service, kit_service, self._context.notifications, self._context.inspector
        )

    def start(self) -> None:
        """No background activity to begin."""

    def stop(self) -> None:
        """No background activity to stop."""

    def shutdown(self) -> None:
        """No resources to release."""

    def _build_page(self) -> WishlistPage:
        assert self._page is not None
        return self._page

    def _build_widget(self) -> WishlistCountWidget:
        assert self._service is not None
        return WishlistCountWidget(self._service)
