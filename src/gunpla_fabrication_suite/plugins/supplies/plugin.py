"""The Supplies plugin entry point."""

from __future__ import annotations

from gunpla_fabrication_suite.plugin_sdk import (
    DashboardWidgetContribution,
    NavigationPageContribution,
    PluginContext,
)
from gunpla_fabrication_suite.plugins.supplies.repositories.supply_repository import (
    SupplyRepository,
)
from gunpla_fabrication_suite.plugins.supplies.services.supply_service import SupplyService
from gunpla_fabrication_suite.plugins.supplies.ui.low_stock_widget import LowStockWidget
from gunpla_fabrication_suite.plugins.supplies.ui.supplies_page import SuppliesPage

PLUGIN_ID = "com.adeptuscraftmatica.gfs.supplies"


class SuppliesPlugin:
    """Owns hobby-supply inventory data: models, repository, service, and UI."""

    plugin_id = PLUGIN_ID

    def __init__(self) -> None:
        self._context: PluginContext | None = None
        self._service: SupplyService | None = None

    def register(self, context: PluginContext) -> None:
        """Register the Supplies navigation page and its dashboard widget."""
        self._context = context

        context.navigation.register(
            self.plugin_id,
            NavigationPageContribution(
                page_id="supplies",
                title="Supplies",
                factory=self._build_page,
                section="main",
                order=40,
            ),
        )
        context.dashboard_widgets.register(
            self.plugin_id,
            DashboardWidgetContribution(
                widget_id="supplies.low_stock",
                title="Low Stock",
                factory=self._build_low_stock_widget,
                order=30,
            ),
        )

    def initialize(self) -> None:
        """Construct the repository and service, and publish the service for other plugins."""
        if self._context is None:
            raise RuntimeError("initialize() called before register()")
        repository = SupplyRepository(self._context.database)
        self._service = SupplyService(repository, self._context.events)
        self._context.services.register_instance(SupplyService, self._service)

    def start(self) -> None:
        """No background activity to begin."""

    def stop(self) -> None:
        """No background activity to stop."""

    def shutdown(self) -> None:
        """No resources to release."""

    def _build_page(self) -> SuppliesPage:
        assert self._service is not None and self._context is not None
        return SuppliesPage(
            self._service,
            self._context.notifications,
            self._context.inspector,
        )

    def _build_low_stock_widget(self) -> LowStockWidget:
        assert self._service is not None
        return LowStockWidget(self._service)
