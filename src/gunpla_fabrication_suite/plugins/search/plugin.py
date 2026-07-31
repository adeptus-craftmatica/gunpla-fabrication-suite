"""The Global Search plugin entry point."""

from __future__ import annotations

from typing import TypeVar

from gunpla_fabrication_suite.plugin_sdk import CommandContribution, PluginContext
from gunpla_fabrication_suite.plugins.build_planner.services.build_service import BuildService
from gunpla_fabrication_suite.plugins.kit_library.services.kit_service import KitService
from gunpla_fabrication_suite.plugins.photography.services.photo_service import PhotoService
from gunpla_fabrication_suite.plugins.search.services.search_index_service import (
    SearchIndexService,
)
from gunpla_fabrication_suite.plugins.search.ui.global_search_dialog import GlobalSearchDialog
from gunpla_fabrication_suite.plugins.supplies.services.supply_service import SupplyService

PLUGIN_ID = "com.adeptuscraftmatica.gfs.search"

T = TypeVar("T")


class GlobalSearchPlugin:
    """A popup, fuzzy-search command reaching across four plugins' data.

    Contributes no navigation page — only a command-palette entry, reached
    via Ctrl+K → "Search Everything…".
    """

    plugin_id = PLUGIN_ID

    def __init__(self) -> None:
        self._context: PluginContext | None = None
        self._index_service: SearchIndexService | None = None

    def register(self, context: PluginContext) -> None:
        """Register the "Search Everything…" command."""
        self._context = context
        context.commands.register(
            self.plugin_id,
            CommandContribution(
                command_id="search.open_everything",
                title="Search Everything…",
                callback=self._open_search,
            ),
        )

    def initialize(self) -> None:
        """Resolve every dependency service and build the search index service.

        Raises:
            RuntimeError: If any dependency plugin's service was not
                published (all should always be, given the declared
                dependencies).
        """
        if self._context is None:
            raise RuntimeError("initialize() called before register()")

        kit_service = self._require(KitService, "Kit Library")
        build_service = self._require(BuildService, "Build Planner")
        photo_service = self._require(PhotoService, "Photography")
        supply_service = self._require(SupplyService, "Supplies")

        self._index_service = SearchIndexService(
            kit_service, build_service, photo_service, supply_service
        )

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
                f"Global Search requires the {plugin_name} plugin's {service_type.__name__}, "
                "which was not found in the service container."
            )
        return service

    def _open_search(self) -> None:
        assert self._context is not None and self._index_service is not None
        dialog = GlobalSearchDialog(
            self._index_service, self._context.navigation, self._context.navigator
        )
        x, y = GlobalSearchDialog.positioned_at_cursor()
        dialog.move(x, y)
        dialog.show()
