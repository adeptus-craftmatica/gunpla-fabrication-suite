"""Tests for the build journal: adding and listing entries."""

from __future__ import annotations

from gunpla_fabrication_suite.plugins.build_planner.schemas import (
    BuildProjectCreate,
    JournalEntryCreate,
)
from gunpla_fabrication_suite.plugins.build_planner.services.build_service import BuildService
from gunpla_fabrication_suite.plugins.build_planner.services.journal_service import JournalService
from gunpla_fabrication_suite.plugins.kit_library.schemas import KitRead


def test_list_entries_is_empty_for_a_new_build(
    journal_service: JournalService, build_service: BuildService, existing_kit: KitRead
) -> None:
    build = build_service.create_build(
        BuildProjectCreate(
            kit_id=existing_kit.id, title="Journal Test", template_key="straight_build"
        )
    )

    assert journal_service.list_entries(build.id) == []


def test_add_entry_appears_in_list(
    journal_service: JournalService, build_service: BuildService, existing_kit: KitRead
) -> None:
    build = build_service.create_build(
        BuildProjectCreate(
            kit_id=existing_kit.id, title="Journal Test", template_key="straight_build"
        )
    )

    journal_service.add_entry(build.id, JournalEntryCreate(note="Primed the torso today."))

    entries = journal_service.list_entries(build.id)
    assert len(entries) == 1
    assert entries[0].note == "Primed the torso today."


def test_entries_are_returned_newest_first(
    journal_service: JournalService, build_service: BuildService, existing_kit: KitRead
) -> None:
    build = build_service.create_build(
        BuildProjectCreate(
            kit_id=existing_kit.id, title="Journal Test", template_key="straight_build"
        )
    )

    journal_service.add_entry(build.id, JournalEntryCreate(note="First entry"))
    journal_service.add_entry(build.id, JournalEntryCreate(note="Second entry"))

    entries = journal_service.list_entries(build.id)
    assert entries[0].note == "Second entry"
    assert entries[1].note == "First entry"
