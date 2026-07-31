"""A plain internal value type — no external input to validate, so a dataclass
rather than Pydantic (same reasoning as ``plugins.stats.schemas``).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SearchResult:
    """One fuzzy-matchable entry in Global Search's flat index."""

    label: str
    entity_type: str
    page_id: str
    entity_id: str
