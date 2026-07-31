"""The Dashboard plugin entry point."""

from __future__ import annotations

from gunpla_fabrication_suite.plugin_sdk import NavigationPageContribution, PluginContext
from gunpla_fabrication_suite.plugins.dashboard.ui.dashboard_page import DashboardPage

PLUGIN_ID = "com.adeptuscraftmatica.gfs.dashboard"


class DashboardPlugin:
    """Contributes the main Dashboard navigation page.

    The dashboard itself owns no domain data — it renders whatever widgets
    other plugins register through :class:`DashboardWidgetRegistry`.
    """

    plugin_id = PLUGIN_ID

    def register(self, context: PluginContext) -> None:
        """Register the Dashboard navigation page."""
        context.navigation.register(
            self.plugin_id,
            NavigationPageContribution(
                page_id="dashboard",
                title="Dashboard",
                factory=lambda: DashboardPage(context.dashboard_widgets, context.layout_manager),
                section="main",
                order=0,
            ),
        )

    def initialize(self) -> None:
        """No internal state to construct; the dashboard has no domain data of its own."""

    def start(self) -> None:
        """No background activity to begin."""

    def stop(self) -> None:
        """No background activity to stop."""

    def shutdown(self) -> None:
        """No resources to release."""
