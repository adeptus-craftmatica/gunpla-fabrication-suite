"""Programmatic Alembic migration coordination.

The core application decides *when* migrations run (at startup, before any
plugin touches the database) and *where* the SQLite file lives. Plugins
decide *what* schema changes look like, by contributing model modules that
get imported (and therefore registered on
:class:`~gunpla_fabrication_suite.core.persistence.base.Base`) before Alembic
autogenerate or upgrade runs — see ``migrations/env.py``.
"""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from gunpla_fabrication_suite.core.logging import get_logger

_logger = get_logger("migrations")


class MigrationsRootNotFoundError(RuntimeError):
    """Raised when the Alembic ``migrations/`` directory cannot be located."""


def resolve_migrations_root() -> Path:
    """Locate the repository's ``migrations/`` directory.

    Walks upward from this file looking for a sibling ``migrations`` folder
    containing an ``env.py``. This works for a source checkout (the
    supported development and initial-release layout); a future packaging
    milestone will bundle migrations as package data for installed wheels.
    """
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
