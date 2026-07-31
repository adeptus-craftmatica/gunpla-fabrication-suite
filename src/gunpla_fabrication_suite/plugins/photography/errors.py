"""Exceptions raised by Photography services."""

from __future__ import annotations


class PhotoNotFoundError(LookupError):
    """Raised when an operation targets a photo id that does not exist."""

    def __init__(self, photo_id: str) -> None:
        super().__init__(f"No photo found with id {photo_id!r}")
        self.photo_id = photo_id


class RelationshipNotFoundError(LookupError):
    """Raised when an operation targets a photo relationship id that does not exist."""

    def __init__(self, relationship_id: str) -> None:
        super().__init__(f"No photo relationship found with id {relationship_id!r}")
        self.relationship_id = relationship_id
