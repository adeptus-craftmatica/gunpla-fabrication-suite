"""Tests for Global Search's flat index builder and fuzzy-match ranking."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from gunpla_fabrication_suite.plugins.build_planner.schemas import BuildProjectCreate
from gunpla_fabrication_suite.plugins.kit_library.schemas import KitCreate
from gunpla_fabrication_suite.plugins.search.services.search_index_service import (
    SearchIndexService,
)
from gunpla_fabrication_suite.shared_ui import fuzzy_score


def _make_jpeg(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (640, 480), color=(200, 40, 40)).save(path, "JPEG")
    return path


def _index_service(kit_service, build_service, photo_service, supply_service):
    return SearchIndexService(kit_service, build_service, photo_service, supply_service)


def test_build_index_includes_all_four_entity_types(
    kit_service,
    build_service,
    photo_service,
    supply_service,
    existing_kit,
    existing_supply,
    tmp_path,
) -> None:
    build_service.create_build(
        BuildProjectCreate(
            kit_id=existing_kit.id, title="Weekend Build", template_key="straight_build"
        )
    )
    photo_service.import_photo(_make_jpeg(tmp_path / "wip.jpg"), caption="Primer coat")

    index = _index_service(kit_service, build_service, photo_service, supply_service).build_index()

    entity_types = {result.entity_type for result in index}
    assert entity_types == {"kit", "build", "photo", "supply"}


def test_build_index_excludes_archived_kits_and_supplies(
    kit_service, build_service, photo_service, supply_service, existing_kit, existing_supply
) -> None:
    kit_service.archive_kit(existing_kit.id)
    supply_service.archive_supply(existing_supply.id)

    index = _index_service(kit_service, build_service, photo_service, supply_service).build_index()

    assert not any(r.entity_type in ("kit", "supply") for r in index)


def test_photo_label_falls_back_to_filename_when_no_caption(
    kit_service, build_service, photo_service, supply_service, tmp_path
) -> None:
    photo = photo_service.import_photo(_make_jpeg(tmp_path / "in_progress.jpg"))

    index = _index_service(kit_service, build_service, photo_service, supply_service).build_index()

    photo_result = next(r for r in index if r.entity_type == "photo")
    assert photo_result.label == photo.original_filename
    assert photo_result.entity_id == photo.id


def test_fuzzy_filter_over_built_index_ranks_substring_matches_first(
    kit_service, build_service, photo_service, supply_service, existing_kit
) -> None:
    kit_service.create_kit(KitCreate(manufacturer="Bandai", name="Zaku II", grade="RG"))

    index = _index_service(kit_service, build_service, photo_service, supply_service).build_index()
    scored = sorted(
        (
            (fuzzy_score("zaku", r.label), r)
            for r in index
            if fuzzy_score("zaku", r.label) is not None
        ),
        key=lambda pair: pair[0],
    )

    assert scored
    assert "zaku" in scored[0][1].label.lower()
