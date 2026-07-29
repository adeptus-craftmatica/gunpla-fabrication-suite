"""Tests for typed settings persistence."""

from __future__ import annotations

from gunpla_fabrication_suite.core.settings import ApplicationSettings, SettingsService


def test_loading_missing_file_returns_defaults(tmp_path) -> None:
    service = SettingsService(tmp_path / "settings.json")

    assert service.current == ApplicationSettings()


def test_save_then_reload_round_trips_values(tmp_path) -> None:
    settings_file = tmp_path / "settings.json"
    service = SettingsService(settings_file)

    settings = service.current
    settings.disabled_plugins = ["com.example.broken"]
    settings.general.theme = "dark"
    service.save(settings)

    reloaded = SettingsService(settings_file)

    assert reloaded.current.disabled_plugins == ["com.example.broken"]
    assert reloaded.current.general.theme == "dark"


def test_save_is_atomic_and_leaves_no_tmp_file(tmp_path) -> None:
    settings_file = tmp_path / "settings.json"
    service = SettingsService(settings_file)

    service.save()

    assert settings_file.exists()
    assert not settings_file.with_suffix(".tmp").exists()


def test_reset_to_defaults_clears_previous_values(tmp_path) -> None:
    settings_file = tmp_path / "settings.json"
    service = SettingsService(settings_file)
    service.current.disabled_plugins = ["something"]
    service.save()

    service.reset_to_defaults()

    assert service.current.disabled_plugins == []
    reloaded = SettingsService(settings_file)
    assert reloaded.current.disabled_plugins == []


def test_corrupt_settings_file_falls_back_to_defaults(tmp_path) -> None:
    settings_file = tmp_path / "settings.json"
    settings_file.write_text("not valid json", encoding="utf-8")

    service = SettingsService(settings_file)

    assert service.current == ApplicationSettings()
