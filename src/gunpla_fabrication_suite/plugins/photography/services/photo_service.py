"""Business logic for importing, attaching, and managing photos.

Import methods here do real file I/O and Pillow processing — callers (UI
code) must run them through :class:`~gunpla_fabrication_suite.core.jobs.BackgroundJobManager`,
never call them directly from a signal handler on the UI thread.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from gunpla_fabrication_suite.core.events import EventBus
from gunpla_fabrication_suite.core.paths import ApplicationPaths
from gunpla_fabrication_suite.plugins.photography.errors import (
    PhotoNotFoundError,
    RelationshipNotFoundError,
)
from gunpla_fabrication_suite.plugins.photography.events import (
    PhotoAttached,
    PhotoDeleted,
    PhotoDetached,
    PhotoImported,
)
from gunpla_fabrication_suite.plugins.photography.models.photo import Photo
from gunpla_fabrication_suite.plugins.photography.models.photo_relationship import (
    PhotoRelationship,
)
from gunpla_fabrication_suite.plugins.photography.repositories.photo_repository import (
    PhotoRepository,
)
from gunpla_fabrication_suite.plugins.photography.schemas import AttachedPhotoRead, PhotoRead
from gunpla_fabrication_suite.plugins.photography.services.media_processor import (
    process_image_file,
)

ProgressReporter = Callable[[int, str], None]


class PhotoService:
    """Imports photos into managed storage and links them to entities."""

    def __init__(
        self, repository: PhotoRepository, paths: ApplicationPaths, events: EventBus
    ) -> None:
        self._repository = repository
        self._paths = paths
        self._events = events

    # -- Import -----------------------------------------------------------------

    def import_photo(self, source_path: Path, *, caption: str | None = None) -> PhotoRead:
        """Import one file, reusing the existing photo if its content is a duplicate.

        Does real file I/O and image processing — run this through
        :class:`~gunpla_fabrication_suite.core.jobs.BackgroundJobManager`.

        Raises:
            FileNotFoundError: If ``source_path`` does not exist.
            gunpla_fabrication_suite.plugins.photography.services.media_processor.UnsupportedImageError:
                If the file cannot be read as an image.
        """
        processed = process_image_file(
            source_path,
            originals_dir=self._paths.media_originals_dir,
            thumbnails_dir=self._paths.media_thumbnails_dir,
            previews_dir=self._paths.media_previews_dir,
        )

        existing = self._repository.find_by_hash(processed.sha256_hash)
        if existing is not None:
            return PhotoRead.from_model(existing)

        photo = Photo(
            sha256_hash=processed.sha256_hash,
            original_filename=source_path.name,
            source_path=str(source_path),
            original_relpath=processed.original_relpath,
            thumbnail_relpath=processed.thumbnail_relpath,
            preview_relpath=processed.preview_relpath,
            width=processed.width,
            height=processed.height,
            file_size_bytes=processed.file_size_bytes,
            exif_json=processed.exif_json,
            caption=caption,
        )
        saved = self._repository.add_photo(photo)
        self._events.publish(
            PhotoImported(
                photo_id=saved.id,
                original_filename=saved.original_filename,
                imported_at=saved.created_at,
            )
        )
        return PhotoRead.from_model(saved)

    def import_photos(
        self,
        source_paths: list[Path],
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
        report_progress: ProgressReporter | None = None,
    ) -> list[PhotoRead]:
        """Import several files, optionally attaching each to the same entity.

        Matches :data:`gunpla_fabrication_suite.core.jobs.manager.JobFunction`'s
        shape (minus the leading progress-reporter-only signature) so it can
        be submitted directly to ``BackgroundJobManager``.
        """
        results: list[PhotoRead] = []
        total = max(len(source_paths), 1)

        for index, path in enumerate(source_paths):
            if report_progress is not None:
                report_progress(round(index / total * 100), f"Importing {path.name}...")
            photo = self.import_photo(path)
            if entity_type is not None and entity_id is not None:
                self._attach(photo.id, entity_type, entity_id)
            results.append(photo)

        if report_progress is not None:
            report_progress(100, "Done")
        return results

    # -- Attachment ---------------------------------------------------------------

    def attach(self, photo_id: str, entity_type: str, entity_id: str) -> AttachedPhotoRead:
        """Link an existing photo to an entity.

        Raises:
            PhotoNotFoundError: If ``photo_id`` does not exist.
        """
        photo = self._require_photo(photo_id)
        relationship = self._attach(photo_id, entity_type, entity_id)
        return self._to_attached_read(relationship, PhotoRead.from_model(photo))

    def _attach(self, photo_id: str, entity_type: str, entity_id: str) -> PhotoRelationship:
        existing = self._repository.list_relationships_for_entity(entity_type, entity_id)
        for relationship in existing:
            if relationship.photo_id == photo_id:
                return relationship

        relationship = PhotoRelationship(
            photo_id=photo_id,
            entity_type=entity_type,
            entity_id=entity_id,
            order_index=len(existing),
        )
        saved = self._repository.add_relationship(relationship)
        self._events.publish(
            PhotoAttached(photo_id=photo_id, entity_type=entity_type, entity_id=entity_id)
        )
        return saved

    def detach(self, relationship_id: str) -> None:
        """Unlink a photo from an entity without deleting the photo itself.

        Raises:
            RelationshipNotFoundError: If ``relationship_id`` does not exist.
        """
        relationship = self._require_relationship(relationship_id)
        self._repository.delete_relationship(relationship_id)
        self._events.publish(
            PhotoDetached(
                photo_id=relationship.photo_id,
                entity_type=relationship.entity_type,
                entity_id=relationship.entity_id,
            )
        )

    def set_hero(self, relationship_id: str) -> None:
        """Mark one relationship as the hero image for its entity, clearing any other.

        Raises:
            RelationshipNotFoundError: If ``relationship_id`` does not exist.
        """
        relationship = self._require_relationship(relationship_id)
        siblings = self._repository.list_relationships_for_entity(
            relationship.entity_type, relationship.entity_id
        )
        for sibling in siblings:
            if sibling.is_hero and sibling.id != relationship_id:
                sibling.is_hero = False
                self._repository.update_relationship(sibling)

        relationship.is_hero = True
        self._repository.update_relationship(relationship)

    def list_photos_for_entity(self, entity_type: str, entity_id: str) -> list[AttachedPhotoRead]:
        """List every photo attached to an entity, in display order."""
        relationships = self._repository.list_relationships_for_entity(entity_type, entity_id)
        results: list[AttachedPhotoRead] = []
        for relationship in relationships:
            photo = self._repository.get_photo(relationship.photo_id)
            if photo is not None:
                results.append(self._to_attached_read(relationship, PhotoRead.from_model(photo)))
        return results

    def count_relationships(self, photo_id: str) -> int:
        """How many entities a photo is currently attached to."""
        return len(self._repository.list_relationships_for_photo(photo_id))

    # -- Library-wide access --------------------------------------------------------

    def list_all_photos(self, *, limit: int | None = None) -> list[PhotoRead]:
        """List every photo in the library, newest first."""
        photos = self._repository.list_all_photos(limit=limit)
        return [PhotoRead.from_model(photo) for photo in photos]

    def get_photo(self, photo_id: str) -> PhotoRead:
        """Fetch a single photo.

        Raises:
            PhotoNotFoundError: If ``photo_id`` does not exist.
        """
        return PhotoRead.from_model(self._require_photo(photo_id))

    def update_details(
        self, photo_id: str, *, caption: str | None, rating: int, rotation_degrees: int
    ) -> PhotoRead:
        """Update a photo's caption, rating, and display rotation.

        Raises:
            PhotoNotFoundError: If ``photo_id`` does not exist.
        """
        photo = self._require_photo(photo_id)
        photo.caption = caption
        photo.rating = max(0, min(5, rating))
        photo.rotation_degrees = rotation_degrees % 360
        saved = self._repository.update_photo(photo)
        return PhotoRead.from_model(saved)

    def delete_photo(self, photo_id: str) -> None:
        """Permanently delete a photo: its row, every relationship, and its managed files.

        Raises:
            PhotoNotFoundError: If ``photo_id`` does not exist.
        """
        photo = self._require_photo(photo_id)
        for relpath, directory in (
            (photo.original_relpath, self._paths.media_originals_dir),
            (photo.thumbnail_relpath, self._paths.media_thumbnails_dir),
            (photo.preview_relpath, self._paths.media_previews_dir),
        ):
            (directory / relpath).unlink(missing_ok=True)

        self._repository.delete_photo(photo_id)
        self._events.publish(PhotoDeleted(photo_id=photo_id))

    def resolve_thumbnail_path(self, photo: PhotoRead) -> Path:
        """Absolute filesystem path to a photo's thumbnail."""
        return self._paths.media_thumbnails_dir / photo.thumbnail_relpath

    def resolve_preview_path(self, photo: PhotoRead) -> Path:
        """Absolute filesystem path to a photo's preview."""
        return self._paths.media_previews_dir / photo.preview_relpath

    # -- Internal helpers ---------------------------------------------------------

    def _require_photo(self, photo_id: str) -> Photo:
        photo = self._repository.get_photo(photo_id)
        if photo is None:
            raise PhotoNotFoundError(photo_id)
        return photo

    def _require_relationship(self, relationship_id: str) -> PhotoRelationship:
        relationship = self._repository.get_relationship(relationship_id)
        if relationship is None:
            raise RelationshipNotFoundError(relationship_id)
        return relationship

    def _to_attached_read(
        self, relationship: PhotoRelationship, photo: PhotoRead
    ) -> AttachedPhotoRead:
        return AttachedPhotoRead(
            relationship_id=relationship.id,
            photo=photo,
            entity_type=relationship.entity_type,
            entity_id=relationship.entity_id,
            is_hero=relationship.is_hero,
            order_index=relationship.order_index,
        )
