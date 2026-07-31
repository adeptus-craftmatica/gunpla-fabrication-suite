"""A tiny fuzzy-match scorer shared by the Command Palette and Global Search."""

from __future__ import annotations


def fuzzy_score(query: str, candidate: str) -> int | None:
    """Return a match quality score (lower is better), or ``None`` if no match.

    Every character of ``query`` must appear in ``candidate`` in order
    (case-insensitively); the score rewards matches that start earlier and
    are more contiguous.
    """
    query = query.lower()
    candidate_lower = candidate.lower()
    if not query:
        return len(candidate_lower)

    position = candidate_lower.find(query)
    if position != -1:
        return position

    cursor = 0
    spread = 0
    for char in query:
        found_at = candidate_lower.find(char, cursor)
        if found_at == -1:
            return None
        spread += found_at - cursor
        cursor = found_at + 1
    return 1000 + spread
