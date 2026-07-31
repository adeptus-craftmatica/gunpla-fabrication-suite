"""Pure image-file processing: hashing, copying, thumbnails, EXIF.

Nothing here touches the database, Qt, or any plugin state — every function
is safe to call from a background thread (see ``core.jobs.BackgroundJobManager``),
which is how ``PhotoService`` uses it. The UI thread must never do this
work directly.

The original source file is only ever copied, never opened for writing —
this module does not modify or overwrite user files.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import ExifTags, Image, ImageOps

_THUMBNAIL_SIZE = (320, 320)
_PREVIEW_MAX_DIMENSION = 1600
_JPEG_QUALITY_THUMBNAIL = 80
_JPEG_QUALITY_PREVIEW = 88

#: A deliberately small, human-relevant subset of EXIF fields — not a full
#: EXIF parser. Extend this tuple if more fields turn out to be useful.
_EXIF_FIELDS = (
    "DateTimeOriginal",
    "Make",
    "Model",
    "FNumber",
    "ExposureTime",
    "ISOSpeedRatings",
    "FocalLength",
)


class UnsupportedImageError(ValueError):
    """Raised when a file cannot be read as an image."""

    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(f"Cannot read {path} as an image: {reason}")
        self.path = path


@dataclass(frozen=True, slots=True)
class ProcessedImageFiles:
    """The outcome of processing one source image into managed storage."""

    sha256_hash: str
    original_relpath: str
    thumbnail_relpath: str
    preview_relpath: str
    width: int
    height: int
    file_size_bytes: int
    exif_json: str | None


def compute_sha256(path: Path) -> str:
    """Hash a file's contents in fixed-size chunks (safe for large files)."""
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _extract_exif_json(image: Image.Image) -> str | None:
    raw_exif = image.getexif()
    if not raw_exif:
        return None

    readable: dict[str, str] = {}
    for tag_id, value in raw_exif.items():
        tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
        if tag_name in _EXIF_FIELDS:
            readable[tag_name] = str(value)

    return json.dumps(readable) if readable else None


def process_image_file(
    source_path: Path,
    *,
    originals_dir: Path,
    thumbnails_dir: Path,
    previews_dir: Path,
) -> ProcessedImageFiles:
    """Hash ``source_path``, copy it into managed storage, and derive a thumbnail/preview.

    Idempotent: if files for this hash already exist (a duplicate import),
    they are not regenerated.

    Raises:
        FileNotFoundError: If ``source_path`` does not exist.
        UnsupportedImageError: If the file cannot be read as an image.
    """
    if not source_path.is_file():
        raise FileNotFoundError(source_path)

    sha256_hash = compute_sha256(source_path)
    file_size_bytes = source_path.stat().st_size
    extension = source_path.suffix.lower() or ".jpg"

    original_relpath = f"{sha256_hash}{extension}"
    thumbnail_relpath = f"{sha256_hash}.jpg"
    preview_relpath = f"{sha256_hash}.jpg"

    original_dest = originals_dir / original_relpath
    thumbnail_dest = thumbnails_dir / thumbnail_relpath
    preview_dest = previews_dir / preview_relpath

    try:
        with Image.open(source_path) as image:
            image.load()
            exif_json = _extract_exif_json(image)
            # EXIF orientation only affects how the *derived* thumbnail/preview
            # display — the copied original's bytes are untouched.
            oriented = ImageOps.exif_transpose(image) or image
            width, height = oriented.size

            if not original_dest.exists():
                shutil.copy2(source_path, original_dest)

            if not thumbnail_dest.exists():
                thumbnail = oriented.convert("RGB")
                thumbnail.thumbnail(_THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
                thumbnail.save(thumbnail_dest, "JPEG", quality=_JPEG_QUALITY_THUMBNAIL)

            if not preview_dest.exists():
                preview = oriented.convert("RGB")
                preview.thumbnail(
                    (_PREVIEW_MAX_DIMENSION, _PREVIEW_MAX_DIMENSION), Image.Resampling.LANCZOS
                )
                preview.save(preview_dest, "JPEG", quality=_JPEG_QUALITY_PREVIEW)
    except (OSError, ValueError) as exc:
        raise UnsupportedImageError(source_path, str(exc)) from exc

    return ProcessedImageFiles(
        sha256_hash=sha256_hash,
        original_relpath=original_relpath,
        thumbnail_relpath=thumbnail_relpath,
        preview_relpath=preview_relpath,
        width=width,
        height=height,
        file_size_bytes=file_size_bytes,
        exif_json=exif_json,
    )
