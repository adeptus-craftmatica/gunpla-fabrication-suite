"""Well-known entity types a photo can be attached to.

Plain string values (not a hard dependency) so any plugin can attach photos
to its own records without Photography ever importing that plugin's models —
the same decoupling used for ``BuildProject.kit_id`` in Build Planner. New
entity types don't require a schema change; unrecognized ones are simply
displayed with their raw value.
"""

from __future__ import annotations

from enum import StrEnum


class PhotoEntityType(StrEnum):
    """Namespaced identifiers for what a photo can be linked to."""

    KIT = "kit_library.kit"
    BUILD = "build_planner.build"
    BUILD_STAGE = "build_planner.stage"
    JOURNAL_ENTRY = "build_planner.journal_entry"
