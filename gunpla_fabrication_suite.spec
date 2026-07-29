# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for Gunpla Fabrication Suite.

Built and driven by scripts/release.py; not intended to be edited by hand
during normal development.

Known limitation: the frozen build does not yet resolve migrations/ the way
the source checkout does (see
gunpla_fabrication_suite.core.persistence.migrations.resolve_migrations_root,
which walks the source tree rather than reading bundled package data).
Packaging polish is tracked as a follow-up milestone in docs/architecture.md;
this spec exists so the release tooling has a real target to build.
"""

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

hidden_imports = collect_submodules("gunpla_fabrication_suite")

a = Analysis(
    ["main.py"],
    pathex=["src"],
    binaries=[],
    datas=[
        ("migrations", "migrations"),
        ("alembic.ini", "."),
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
        "CFBundleShortVersionString": "0.1.0",
        "CFBundleVersion": "0.1.0",
        "NSHumanReadableCopyright": "Copyright Adeptus Craftmatica",
    },
)
