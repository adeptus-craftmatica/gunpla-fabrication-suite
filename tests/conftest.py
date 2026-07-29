"""Shared pytest fixtures."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from gunpla_fabrication_suite.core.events import EventBus
from gunpla_fabrication_suite.core.paths import ApplicationPaths
from gunpla_fabrication_suite.core.persistence import DatabaseService


@pytest.fixture
def app_paths(tmp_path):
    """A fully isolated set of application directories under pytest's tmp_path."""
    paths = ApplicationPaths(root=tmp_path)
    paths.ensure_exists()
    return paths


@pytest.fixture
def database(app_paths):
    """A migrated, isolated SQLite database for the duration of one test."""
    db = DatabaseService(app_paths.database_file)
    db.migrate()
    yield db
    db.dispose()


@pytest.fixture
def event_bus():
    """A fresh, empty event bus."""
    return EventBus()
