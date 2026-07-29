"""Registries that collect plugin contributions for the shell to render.

Each registry tracks which plugin owns each contribution so that disabling
or reloading a plugin can cleanly remove exactly its contributions.
"""

from __future__ import annotations

from gunpla_fabrication_suite.plugin_sdk.contracts import (
    CommandContribution,
    DashboardWidgetContribution,
    NavigationPageContribution,
)


class NavigationRegistry:
    """Collects navigation pages contributed by plugins."""

    def __init__(self) -> None:
        self._pages: dict[str, tuple[str, NavigationPageContribution]] = {}

    def register(self, plugin_id: str, contribution: NavigationPageContribution) -> None:
        """Add a navigation page owned by ``plugin_id``."""
        self._pages[contribution.page_id] = (plugin_id, contribution)

    def unregister_all_for(self, plugin_id: str) -> None:
        """Remove every page owned by ``plugin_id``."""
        for page_id, (owner, _) in list(self._pages.items()):
            if owner == plugin_id:
                del self._pages[page_id]

    def all_pages(self) -> tuple[NavigationPageContribution, ...]:
        """Every registered page, ordered for display."""
        return tuple(
            sorted((c for _, c in self._pages.values()), key=lambda c: (c.section, c.order))
        )


class DashboardWidgetRegistry:
    """Collects dashboard widgets contributed by plugins."""

    def __init__(self) -> None:
        self._widgets: dict[str, tuple[str, DashboardWidgetContribution]] = {}

    def register(self, plugin_id: str, contribution: DashboardWidgetContribution) -> None:
        """Add a dashboard widget owned by ``plugin_id``."""
        self._widgets[contribution.widget_id] = (plugin_id, contribution)

    def unregister_all_for(self, plugin_id: str) -> None:
        """Remove every widget owned by ``plugin_id``."""
        for widget_id, (owner, _) in list(self._widgets.items()):
            if owner == plugin_id:
                del self._widgets[widget_id]

    def all_widgets(self) -> tuple[DashboardWidgetContribution, ...]:
        """Every registered widget, ordered for display."""
        return tuple(sorted((c for _, c in self._widgets.values()), key=lambda c: c.order))


class CommandRegistry:
    """Collects command-palette actions contributed by plugins."""

    def __init__(self) -> None:
        self._commands: dict[str, tuple[str, CommandContribution]] = {}

    def register(self, plugin_id: str, contribution: CommandContribution) -> None:
        """Add a command owned by ``plugin_id``."""
        self._commands[contribution.command_id] = (plugin_id, contribution)

    def unregister_all_for(self, plugin_id: str) -> None:
        """Remove every command owned by ``plugin_id``."""
        for command_id, (owner, _) in list(self._commands.items()):
            if owner == plugin_id:
                del self._commands[command_id]

    def all_commands(self) -> tuple[CommandContribution, ...]:
        """Every registered command, in registration order."""
        return tuple(c for _, c in self._commands.values())
