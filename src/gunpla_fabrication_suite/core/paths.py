"""Operating-system-appropriate application data locations.

All filesystem locations used by the application are resolved through
:class:`ApplicationPaths` rather than hardcoded, so the same code behaves
correctly on Windows, macOS, and Linux.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from platformdirs import PlatformDirs

_APP_NAME = "GunplaFabricationSuite"
_APP_AUTHOR = "AdeptusCraftmatica"


@dataclass(frozen=True, slots=True)
class ApplicationPaths:
    """Resolved, OS-appropriate directories used by the application.

    Directories are computed lazily from a :class:`~platformdirs.PlatformDirs`
    instance and are not created until :meth:`ensure_exists` is called, so
    tests can point this at a temporary root without touching the real user
    data directory.
    """

    root: Path
    database_dir: Path = field(init=False)
    media_dir: Path = field(init=False)
    media_originals_dir: Path = field(init=False)
    media_previews_dir: Path = field(init=False)
    media_thumbnails_dir: Path = field(init=False)
    media_exports_dir: Path = field(init=False)
    imports_dir: Path = field(init=False)
    exports_dir: Path = field(init=False)
    backups_dir: Path = field(init=False)
    cache_dir: Path = field(init=False)
    logs_dir: Path = field(init=False)
    plugins_dir: Path = field(init=False)
    recovery_dir: Path = field(init=False)
    settings_file: Path = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "database_dir", self.root / "database")
        object.__setattr__(self, "media_dir", self.root / "media")
        object.__setattr__(self, "media_originals_dir", self.root / "media" / "originals")
        object.__setattr__(self, "media_previews_dir", self.root / "media" / "previews")
        object.__setattr__(self, "media_thumbnails_dir", self.root / "media" / "thumbnails")
        object.__setattr__(self, "media_exports_dir", self.root / "media" / "exports")
        object.__setattr__(self, "imports_dir", self.root / "imports")
        object.__setattr__(self, "exports_dir", self.root / "exports")
        object.__setattr__(self, "backups_dir", self.root / "backups")
        object.__setattr__(self, "cache_dir", self.root / "cache")
        object.__setattr__(self, "logs_dir", self.root / "logs")
        object.__setattr__(self, "plugins_dir", self.root / "plugins")
        object.__setattr__(self, "recovery_dir", self.root / "recovery")
        object.__setattr__(self, "settings_file", self.root / "settings.json")

    @property
    def database_file(self) -> Path:
        """Path to the primary SQLite database file."""
        return self.database_dir / "gunpla_fabrication_suite.sqlite3"

    def all_directories(self) -> tuple[Path, ...]:
        """Every managed directory that must exist before the app runs."""
        return (
            self.database_dir,
            self.media_originals_dir,
            self.media_previews_dir,
            self.media_thumbnails_dir,
            self.media_exports_dir,
            self.imports_dir,
            self.exports_dir,
            self.backups_dir,
            self.cache_dir,
            self.logs_dir,
            self.plugins_dir,
            self.recovery_dir,
        )

    def ensure_exists(self) -> None:
        """Create every managed directory, including parents, if missing."""
        for directory in self.all_directories():
            directory.mkdir(parents=True, exist_ok=True)


def resolve_application_paths(*, override_root: Path | None = None) -> ApplicationPaths:
    """Resolve the managed data directories for this OS and user.

    Args:
        override_root: When provided, used as the root instead of the
            platform-specific user data directory. Intended for tests.
    """
    if override_root is not None:
        return ApplicationPaths(root=override_root)

    dirs = PlatformDirs(appname=_APP_NAME, appauthor=_APP_AUTHOR, roaming=True)
    return ApplicationPaths(root=Path(dirs.user_data_dir))
