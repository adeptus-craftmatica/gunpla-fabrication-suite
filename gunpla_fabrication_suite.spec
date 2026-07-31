# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for Gunpla Fabrication Suite.

Built and driven by scripts/release.py; not intended to be edited by hand
during normal development.

Two things a frozen build cannot get "for free" the way a source checkout
can, both bundled explicitly below as plain *data* (not Python modules):

- migrations/ — resolved at runtime by
  gunpla_fabrication_suite.core.persistence.migrations.resolve_migrations_root
- each built-in plugin's manifest.toml — resolved at runtime by
  gunpla_fabrication_suite.core.plugins.discovery._builtin_plugins_root

Both resolvers check ``sys.frozen``/``sys._MEIPASS`` and fall back to walking
the source tree otherwise, so the exact same code path works in development
and in a packaged build.
"""

import glob
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

hidden_imports = collect_submodules("gunpla_fabrication_suite")
# migrations/env.py is bundled as plain *data*, then loaded dynamically by
# Alembic at runtime (see resolve_migrations_root's docstring) — PyInstaller's
# static import analysis never traces it, so any import it needs that isn't
# *also* used somewhere in the statically-traced code must be listed here by
# hand. alembic/sqlalchemy are already covered because the traced code
# imports them directly; logging.config is the one env.py-only import.
hidden_imports.append("logging.config")

# One (source, dest) pair per plugin's manifest.toml, so discovery can find
# them at sys._MEIPASS/gunpla_fabrication_suite/plugins/<plugin>/manifest.toml
# — the same relative layout as the source tree, just rooted differently.
manifest_datas = [
    (manifest_path, f"gunpla_fabrication_suite/plugins/{Path(manifest_path).parent.name}")
    for manifest_path in glob.glob("src/gunpla_fabrication_suite/plugins/*/manifest.toml")
]
if not manifest_datas:
    raise RuntimeError(
        "No plugin manifest.toml files found under src/gunpla_fabrication_suite/plugins/ "
        "— run this spec from the project root."
    )

a = Analysis(
    ["main.py"],
    pathex=["src"],
    binaries=[],
    datas=[
        ("migrations", "migrations"),
        ("alembic.ini", "."),
        *manifest_datas,
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="gunpla-fabrication-suite",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="GunplaFabricationSuite",
)

app = BUNDLE(
    coll,
    name="GunplaFabricationSuite.app",
    icon=None,
    bundle_identifier="com.adeptuscraftmatica.gfs",
    info_plist={
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1.0.0",
        "NSHumanReadableCopyright": "Copyright Adeptus Craftmatica",
    },
)
