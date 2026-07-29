"""Plugin manifest schema and TOML loading."""

from __future__ import annotations

import tomllib
from pathlib import Path

from pydantic import BaseModel, Field


class PluginManifest(BaseModel):
    """The validated contents of a plugin's ``manifest.toml``."""

    id: str
    name: str
    version: str
    api_version: str
    entry_point: str
    description: str = ""
    author: str = ""
    dependencies: list[str] = Field(default_factory=list)
    optional_dependencies: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)


def load_manifest(manifest_path: Path) -> PluginManifest:
    """Parse and validate a ``manifest.toml`` file.

    Raises:
        FileNotFoundError: If ``manifest_path`` does not exist.
        pydantic.ValidationError: If required fields are missing or invalid.
    """
    raw = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    return PluginManifest.model_validate(raw)
