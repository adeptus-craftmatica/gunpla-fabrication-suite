"""The metadata written to ``manifest.json`` at the root of every backup zip."""

from __future__ import annotations

from pydantic import BaseModel

BACKUP_FORMAT_VERSION = 1


class BackupManifest(BaseModel):
    """Identifies and describes one backup archive."""

    format_version: int
    app_version: str
    export_timestamp: str
    schema_revision: str | None = None
