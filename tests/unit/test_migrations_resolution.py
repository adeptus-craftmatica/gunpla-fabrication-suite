"""Tests for locating the ``migrations/`` directory in both dev and frozen builds.

A frozen PyInstaller build has no source tree to walk — these tests cover
the ``sys.frozen``/``sys._MEIPASS`` branch that a normal (non-frozen) test
run never otherwise exercises. See the docstring on
``resolve_migrations_root`` for why this distinction exists.
"""

from __future__ import annotations

import pytest

from gunpla_fabrication_suite.core.persistence.migrations import (
    MigrationsRootNotFoundError,
    resolve_migrations_root,
)


def test_resolve_migrations_root_finds_it_in_a_source_checkout() -> None:
    root = resolve_migrations_root()

    assert root.name == "migrations"
    assert (root / "env.py").is_file()


def test_resolve_migrations_root_uses_meipass_when_frozen(monkeypatch, tmp_path) -> None:
    bundled = tmp_path / "migrations"
    bundled.mkdir()
    (bundled / "env.py").write_text("# fake bundled env.py", encoding="utf-8")

    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.setattr("sys._MEIPASS", str(tmp_path), raising=False)

    root = resolve_migrations_root()

    assert root == bundled


def test_resolve_migrations_root_raises_when_frozen_bundle_is_missing_migrations(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.setattr("sys._MEIPASS", str(tmp_path), raising=False)

    with pytest.raises(MigrationsRootNotFoundError):
        resolve_migrations_root()


def test_resolve_migrations_root_raises_when_frozen_but_meipass_unset(monkeypatch) -> None:
    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.delattr("sys._MEIPASS", raising=False)

    with pytest.raises(MigrationsRootNotFoundError):
        resolve_migrations_root()
