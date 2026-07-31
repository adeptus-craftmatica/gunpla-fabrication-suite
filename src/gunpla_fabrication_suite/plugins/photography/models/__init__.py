"""Photography ORM models."""

from __future__ import annotations

from gunpla_fabrication_suite.plugins.photography.models.entity_types import PhotoEntityType
from gunpla_fabrication_suite.plugins.photography.models.photo import Photo
from gunpla_fabrication_suite.plugins.photography.models.photo_relationship import (
    PhotoRelationship,
)

__all__ = ["Photo", "PhotoEntityType", "PhotoRelationship"]
