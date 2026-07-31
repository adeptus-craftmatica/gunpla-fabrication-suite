"""Programmatic Alembic migration coordination.

The core application decides *when* migrations run (at startup, before any
plugin touches the database) and *where* the SQLite file lives. Plugins
decide *what* schema changes look like, by contributing model modules that
get imported (and therefore registered on
:class:`~gunpla_fabrication_suite.core.persistence.base.Base`) before Alembic
autogenerate or upgrade runs — see ``migrations/env.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

from gunpla_fabrication_suite.core.logging import get_logger

_logger = get_logger("migrations")


class MigrationsRootNotFoundError(RuntimeError):
    """Raised when the Alembic ``migrations/`` directory cannot be located."""


def resolve_migrations_root() -> Path:
    """Locate the ``migrations/`` directory, for a source checkout or a frozen build.

    A frozen PyInstaller build has no source tree to walk: pure-Python
    modules (including this one) are compiled into the ``PYZ`` archive, so
    ``Path(__file__)`` does not point at a real, walkable directory the way
    it does in development. ``migrations/`` is instead bundled as plain
    *data* (see ``datas`` in ``gunpla_fabrication_suite.spec``), which
    PyInstaller extracts to a real directory at ``sys._MEIPASS`` and
    exposes for exactly this purpose — see the PyInstaller docs on
    "Run-time Information".
    """
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass is None:
            raise MigrationsRootNotFoundError(
                "Running as a frozen build but sys._MEIPASS is unset — "
                "this PyInstaller build is not configured as expected."
            )
        candidate = Path(meipass) / "migrations"
        if (candidate / "env.py").is_file():
            return candidate
        raise MigrationsRootNotFoundError(
            f"Could not locate the bundled 'migrations' directory at {candidate}. "
            "Check the `datas` entry in gunpla_fabrication_suite.spec."
        )

    for parent in Path(__file__).resolve().parents:
        candidate = parent / "migrations"
        if (candidate / "env.py").is_file():
            return candidate
    raise MigrationsRootNotFoundError(
        "Could not locate the 'migrations' directory relative to the installed package."
    )


def build_alembic_config(database_file: Path, migrations_root: Path | None = None) -> Config:
    """Build an in-memory Alembic configuration targeting ``database_file``."""
    root = migrations_root or resolve_migrations_root()
    config = Config()
    config.set_main_option("script_location", str(root))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_file}")
    return config


def run_migrations(database_file: Path, migrations_root: Path | None = None) -> None:
    """Upgrade ``database_file`` to the latest ("head") schema revision."""
    config = build_alembic_config(database_file, migrations_root)
    _logger.info("migrations_starting", database=str(database_file))
    command.upgrade(config, "head")
    _logger.info("migrations_complete", database=str(database_file))
