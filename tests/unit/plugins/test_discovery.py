"""Tests for locating built-in plugins' manifests in both dev and frozen builds.

A frozen PyInstaller build has no source tree to walk — these tests cover
the ``sys.frozen``/``sys._MEIPASS`` branch that a normal (non-frozen) test
run never otherwise exercises. See the docstring on ``_builtin_plugins_root``
for why this distinction exists.
"""

from __future__ import annotations

import pytest

from gunpla_fabrication_suite.core.plugins.discovery import (
    _builtin_plugins_root,
    discover_builtin_plugins,
)


def test_builtin_plugins_root_finds_it_in_a_source_checkout() -> None:
    root = _builtin_plugins_root()

    assert root.name == "plugins"
    assert (root / "kit_library" / "manifest.toml").is_file()


def test_builtin_plugins_root_uses_meipass_when_frozen(monkeypatch, tmp_path) -> None:
    bundled = tmp_path / "gunpla_fabrication_suite" / "plugins"
    bundled.mkdir(parents=True)

    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.setattr("sys._MEIPASS", str(tmp_path), raising=False)

    root = _builtin_plugins_root()

    assert root == bundled


def test_builtin_plugins_root_raises_when_frozen_but_meipass_unset(monkeypatch) -> None:
    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.delattr("sys._MEIPASS", raising=False)

    with pytest.raises(RuntimeError, match="MEIPASS"):
        _builtin_plugins_root()


def test_discover_builtin_plugins_finds_manifest_in_a_frozen_style_layout(
    monkeypatch, tmp_path
) -> None:
    """A minimal end-to-end check: a bundled-looking manifest.toml is discovered."""
    plugin_dir = tmp_path / "gunpla_fabrication_suite" / "plugins" / "fake_plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "manifest.toml").write_text(
        """
        id = "com.example.fake"
        name = "Fake Plugin"
        version = "1.0.0"
        api_version = "1"
        entry_point = "plugin:FakePlugin"
        """,
        encoding="utf-8",
    )

    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.setattr("sys._MEIPASS", str(tmp_path), raising=False)

    discovered = discover_builtin_plugins()

    assert [plugin.manifest.id for plugin in discovered] == ["com.example.fake"]
    assert discovered[0].module_name == "gunpla_fabrication_suite.plugins.fake_plugin.plugin"
