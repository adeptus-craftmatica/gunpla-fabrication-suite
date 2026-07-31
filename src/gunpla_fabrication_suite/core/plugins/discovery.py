"""Locates plugins from built-in packages, the user plugin directory, and entry points."""

from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass
from importlib.metadata import entry_points
from pathlib import Path

from gunpla_fabrication_suite.core.logging import get_logger
from gunpla_fabrication_suite.plugin_sdk.manifest import PluginManifest, load_manifest

_logger = get_logger("plugins")

ENTRY_POINT_GROUP = "gunpla_fabrication_suite.plugins"

#: Model modules imported so their tables register on the shared declarative
#: ``Base`` before Alembic inspects metadata. A plugin with persisted models
#: must add its model module(s) here.
MODEL_MODULES: tuple[str, ...] = (
    "gunpla_fabrication_suite.plugins.kit_library.models.kit",
    "gunpla_fabrication_suite.plugins.build_planner.models.build_project",
    "gunpla_fabrication_suite.plugins.build_planner.models.build_stage",
    "gunpla_fabrication_suite.plugins.build_planner.models.build_task",
    "gunpla_fabrication_suite.plugins.build_planner.models.work_session",
    "gunpla_fabrication_suite.plugins.build_planner.models.journal_entry",
    "gunpla_fabrication_suite.plugins.build_planner.models.supply_usage",
    "gunpla_fabrication_suite.plugins.photography.models.photo",
    "gunpla_fabrication_suite.plugins.photography.models.photo_relationship",
    "gunpla_fabrication_suite.plugins.supplies.models.supply",
)


@dataclass(frozen=True, slots=True)
class DiscoveredPlugin:
    """A plugin found by discovery, not yet imported or instantiated."""

    manifest: PluginManifest
    module_name: str
    class_name: str
    source: str


def _builtin_plugins_root() -> Path:
    """Locate the ``plugins/`` directory holding each built-in plugin's ``manifest.toml``.

    A frozen PyInstaller build has no source tree: ``plugins_package.__file__``
    points at a synthetic path inside the bundled ``PYZ`` archive, not a real,
    listable directory. Each plugin's ``manifest.toml`` is bundled separately
    as plain *data* (see ``datas`` in ``gunpla_fabrication_suite.spec``),
    extracted to a real directory at ``sys._MEIPASS`` — mirroring
    ``resolve_migrations_root`` in ``core.persistence.migrations``, which
    hits the exact same problem for the same reason.
    """
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass is None:
            raise RuntimeError(
                "Running as a frozen build but sys._MEIPASS is unset — "
                "this PyInstaller build is not configured as expected."
            )
        return Path(meipass) / "gunpla_fabrication_suite" / "plugins"

    from gunpla_fabrication_suite import plugins as plugins_package

    return Path(plugins_package.__file__).parent


def _manifest_entry_point(manifest: PluginManifest) -> tuple[str, str]:
    module_suffix, separator, class_name = manifest.entry_point.partition(":")
    if not separator:
        raise ValueError(
            f"Manifest for {manifest.id!r} has an invalid entry_point "
            f"{manifest.entry_point!r}; expected 'module:ClassName'."
        )
    return module_suffix, class_name


def discover_builtin_plugins() -> list[DiscoveredPlugin]:
    """Find every built-in plugin package under ``gunpla_fabrication_suite.plugins``."""
    discovered: list[DiscoveredPlugin] = []
    for entry in sorted(_builtin_plugins_root().iterdir()):
        manifest_path = entry / "manifest.toml"
        if not entry.is_dir() or not manifest_path.is_file():
            continue
        try:
            manifest = load_manifest(manifest_path)
            module_suffix, class_name = _manifest_entry_point(manifest)
        except Exception:
            _logger.exception("manifest_load_failed", path=str(manifest_path))
            continue
        module_name = f"gunpla_fabrication_suite.plugins.{entry.name}.{module_suffix}"
        discovered.append(
            DiscoveredPlugin(
                manifest=manifest,
                module_name=module_name,
                class_name=class_name,
                source="builtin",
            )
        )
    return discovered


def discover_user_plugins(user_plugins_dir: Path) -> list[DiscoveredPlugin]:
    """Find plugins dropped into the user's plugin directory, each its own package."""
    discovered: list[DiscoveredPlugin] = []
    if not user_plugins_dir.is_dir():
        return discovered

    if str(user_plugins_dir) not in sys.path:
        sys.path.insert(0, str(user_plugins_dir))

    for entry in sorted(user_plugins_dir.iterdir()):
        manifest_path = entry / "manifest.toml"
        if not entry.is_dir() or not manifest_path.is_file():
            continue
        try:
            manifest = load_manifest(manifest_path)
            module_suffix, class_name = _manifest_entry_point(manifest)
        except Exception:
            _logger.exception("manifest_load_failed", path=str(manifest_path))
            continue
        discovered.append(
            DiscoveredPlugin(
                manifest=manifest,
                module_name=f"{entry.name}.{module_suffix}",
                class_name=class_name,
                source="user",
            )
        )
    return discovered


def discover_entry_point_plugins() -> list[DiscoveredPlugin]:
    """Find third-party plugins registered under the plugin entry-point group.

    Each entry point must resolve to the plugin's class module; that module's
    package must contain a sibling ``manifest.toml``.
    """
    discovered: list[DiscoveredPlugin] = []
    for ep in entry_points(group=ENTRY_POINT_GROUP):
        module_name, separator, class_name = ep.value.partition(":")
        if not separator:
            _logger.error("entry_point_invalid", entry_point=ep.name, value=ep.value)
            continue
        try:
            module = importlib.import_module(module_name)
            if module.__file__ is None:
                raise ValueError(f"Module {module_name!r} has no __file__ (namespace package?)")
            manifest_path = Path(module.__file__).parent / "manifest.toml"
            manifest = load_manifest(manifest_path)
        except Exception:
            _logger.exception("entry_point_plugin_discovery_failed", entry_point=ep.name)
            continue
        discovered.append(
            DiscoveredPlugin(
                manifest=manifest,
                module_name=module_name,
                class_name=class_name,
                source="entry_point",
            )
        )
    return discovered


def discover_all_plugins(user_plugins_dir: Path) -> list[DiscoveredPlugin]:
    """Discover built-in, user-directory, and entry-point plugins, in that order."""
    return [
        *discover_builtin_plugins(),
        *discover_user_plugins(user_plugins_dir),
        *discover_entry_point_plugins(),
    ]


def import_all_model_modules() -> None:
    """Import every plugin model module so its tables register on ``Base``."""
    for module_name in MODEL_MODULES:
        importlib.import_module(module_name)
