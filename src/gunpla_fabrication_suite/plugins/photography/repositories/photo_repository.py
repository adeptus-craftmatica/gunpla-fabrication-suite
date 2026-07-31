"""Repository for :class:`Photo` and :class:`PhotoRelationship` rows.

This is the only place in the plugin that issues SQLAlchemy queries against
these tables; the service layer and UI never do.
"""

from __future__ import annotations

from sqlalchemy import select

from gunpla_fabrication_suite.core.persistence import DatabaseService
from gunpla_fabrication_suite.plugins.photography.models.photo import Photo
from gunpla_fabrication_suite.plugins.photography.models.photo_relationship import (
    PhotoRelationship,
)


class PhotoRepository:
    """CRUD and query access to photos and their entity relationships."""

    def __init__(self, database: DatabaseService) -> None:
        self._database = database

    # -- Photos -----------------------------------------------------------------

    def add_photo(self, photo: Photo) -> Photo:
        """Insert a new photo row."""
        with self._database.session() as session:
            session.add(photo)
            session.flush()
            session.refresh(photo)
            session.expunge(photo)
            return photo

    def get_photo(self, photo_id: str) -> Photo | None:
        """Fetch a photo by id."""
        with self._database.session() as session:
            photo = session.get(Photo, photo_id)
            if photo is not None:
                session.expunge(photo)
            return photo

    def find_by_hash(self, sha256_hash: str) -> Photo | None:
        """Find an already-imported photo with this exact content hash, if any."""
        with self._database.session() as session:
            statement = select(Photo).where(Photo.sha256_hash == sha256_hash)
            photo = session.scalars(statement).first()
            if photo is not None:
                session.expunge(photo)
            return photo

    def list_all_photos(self, *, limit: int | None = None) -> list[Photo]:
        """List every photo in the library, newest first."""
        with self._database.session() as session:
            statement = select(Photo).order_by(Photo.created_at.desc())
            if limit is not None:
                statement = statement.limit(limit)
            photos = list(session.scalars(statement))
            for photo in photos:
                session.expunge(photo)
            return photos

    def update_photo(self, photo: Photo) -> Photo:
        """Merge changes to an existing photo back into the database."""
        with self._database.session() as session:
            merged = session.merge(photo)
            session.flush()
            session.refresh(merged)
            session.expunge(merged)
            return merged

    def delete_photo(self, photo_id: str) -> None:
        """Permanently remove a photo row (relationships cascade)."""
        with self._database.session() as session:
            photo = session.get(Photo, photo_id)
            if photo is not None:
                session.delete(photo)

    # -- Relationships ------------------------------------------------------------

    def add_relationship(self, relationship: PhotoRelationship) -> PhotoRelationship:
        """Insert a new photo-to-entity relationship."""
        with self._database.session() as session:
            session.add(relationship)
            session.flush()
            session.refresh(relationship)
            session.expunge(relationship)
            return relationship

    def get_relationship(self, relationship_id: str) -> PhotoRelationship | None:
        """Fetch a relationship by id."""
        with self._database.session() as session:
            relationship = session.get(PhotoRelationship, relationship_id)
            if relationship is not None:
                session.expunge(relationship)
            return relationship

    def list_relationships_for_entity(
        self, entity_type: str, entity_id: str
    ) -> list[PhotoRelationship]:
        """List an entity's photo relationships in display order."""
        with self._database.session() as session:
            statement = (
                select(PhotoRelationship)
                .where(
                    PhotoRelationship.entity_type == entity_type,
                    PhotoRelationship.entity_id == entity_id,
                )
                .order_by(PhotoRelationship.order_index)
            )
            relationships = list(session.scalars(statement))
            for relationship in relationships:
                session.expunge(relationship)
            return relationships

    def list_relationships_for_photo(self, photo_id: str) -> list[PhotoRelationship]:
        """List every entity a photo is attached to."""
        with self._database.session() as session:
            statement = select(PhotoRelationship).where(PhotoRelationship.photo_id == photo_id)
            relationships = list(session.scalars(statement))
            for relationship in relationships:
                session.expunge(relationship)
            return relationships

    def update_relationship(self, relationship: PhotoRelationship) -> PhotoRelationship:
        """Merge changes to an existing relationship back into the database."""
        with self._database.session() as session:
            merged = session.merge(relationship)
            session.flush()
            session.refresh(merged)
            session.expunge(merged)
            return merged

    def delete_relationship(self, relationship_id: str) -> None:
        """Permanently remove a relationship (does not delete the photo itself)."""
        with self._database.session() as session:
            relationship = session.get(PhotoRelationship, relationship_id)
            if relationship is not None:
                session.delete(relationship)
