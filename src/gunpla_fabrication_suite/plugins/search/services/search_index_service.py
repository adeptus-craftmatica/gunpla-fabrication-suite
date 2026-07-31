"""Builds the flat, searchable list Global Search fuzzy-matches against."""

from __future__ import annotations

from gunpla_fabrication_suite.plugins.build_planner.services.build_service import BuildService
from gunpla_fabrication_suite.plugins.kit_library.services.kit_service import KitService
from gunpla_fabrication_suite.plugins.photography.services.photo_service import PhotoService
from gunpla_fabrication_suite.plugins.search.schemas import SearchResult
from gunpla_fabrication_suite.plugins.supplies.services.supply_service import SupplyService


class SearchIndexService:
    """Builds the flat index Global Search filters against.

    Rebuilt fresh each time the search dialog opens (not cached across
    opens) so results always reflect the current collection — cheap at
    hobbyist scale, same reasoning as ``StatsService``.
    """

    def __init__(
        self,
        kit_service: KitService,
        build_service: BuildService,
        photo_service: PhotoService,
        supply_service: SupplyService,
    ) -> None:
        self._kit_service = kit_service
        self._build_service = build_service
        self._photo_service = photo_service
        self._supply_service = supply_service

    def build_index(self) -> list[SearchResult]:
        """Assemble one flat list of every kit, build, photo, and supply."""
        results: list[SearchResult] = []

        for kit in self._kit_service.list_kits(include_archived=False):
            label = " — ".join(
                part
                for part in (
                    kit.manufacturer,
                    kit.name,
                    kit.mobile_suit_designation,
                    kit.product_number,
                    kit.series,
                )
                if part
            )
            results.append(SearchResult(label, "kit", "kit_library", kit.id))

        for build in self._build_service.list_builds(include_archived=False):
            results.append(SearchResult(build.title, "build", "build_planner", build.id))

        for photo in self._photo_service.list_all_photos():
            label = photo.caption or photo.original_filename
            results.append(SearchResult(label, "photo", "photo_library", photo.id))

        for supply in self._supply_service.list_supplies(include_archived=False):
            label = " — ".join(
                part for part in (supply.brand, supply.name, supply.color_name) if part
            )
            results.append(SearchResult(label, "supply", "supplies", supply.id))

        return results
