"""Integration tests for Alembic migration coordination against a real SQLite file."""

from __future__ import annotations

from sqlalchemy import inspect

from gunpla_fabrication_suite.core.persistence import DatabaseService


def test_migrate_creates_expected_tables(app_paths) -> None:
    db = DatabaseService(app_paths.database_file)

    db.migrate()

    table_names = set(inspect(db.engine).get_table_names())
    assert "kit_library_kits" in table_names
    assert {
        "build_planner_projects",
        "build_planner_stages",
        "build_planner_tasks",
        "build_planner_work_sessions",
        "build_planner_journal_entries",
    } <= table_names
    assert {"photography_photos", "photography_photo_relationships"} <= table_names
    db.dispose()


def test_migrate_is_idempotent(app_paths) -> None:
    db = DatabaseService(app_paths.database_file)

    db.migrate()
    db.migrate()  # must not raise or duplicate anything

    inspector = inspect(db.engine)
    assert inspector.get_table_names().count("kit_library_kits") == 1
    db.dispose()


def test_migrated_database_passes_integrity_check(app_paths) -> None:
    db = DatabaseService(app_paths.database_file)
    db.migrate()

    assert db.check_integrity() is True
    db.dispose()


def test_kit_table_has_expected_columns(app_paths) -> None:
    db = DatabaseService(app_paths.database_file)
    db.migrate()

    inspector = inspect(db.engine)
    columns = {column["name"] for column in inspector.get_columns("kit_library_kits")}

    assert {"id", "manufacturer", "name", "grade", "status", "created_at", "updated_at"} <= columns
    db.dispose()
