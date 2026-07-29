"""Alembic environment.

This file is used two ways:

1. Programmatically, by :func:`gunpla_fabrication_suite.core.persistence.migrations.run_migrations`,
   which builds an in-memory ``Config`` with ``sqlalchemy.url`` already set to
   the real application database — this is how the app upgrades its own
   database at startup.
2. From the command line (``alembic revision --autogenerate``, ``alembic
   upgrade head``) during development, in which case the database URL falls
   back to ``GFS_DATABASE_URL`` or the platform default data directory.

Either way, every built-in plugin's model modules are imported first so their
tables are registered on the shared declarative ``Base`` before Alembic
inspects metadata.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from gunpla_fabrication_suite.core.paths import resolve_application_paths
from gunpla_fabrication_suite.core.persistence.base import Base
from gunpla_fabrication_suite.core.plugins.discovery import import_all_model_modules

config = context.config

if config.config_file_name is not None and os.path.exists(config.config_file_name):
    fileConfig(config.config_file_name)

import_all_model_modules()
target_metadata = Base.metadata

if not config.get_main_option("sqlalchemy.url"):
    default_url = f"sqlite:///{resolve_application_paths().database_file}"
    config.set_main_option("sqlalchemy.url", os.environ.get("GFS_DATABASE_URL", default_url))


def run_migrations_offline() -> None:
    """Run migrations without a live DBAPI connection, emitting SQL to stdout."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
