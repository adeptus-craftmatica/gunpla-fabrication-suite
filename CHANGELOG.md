# Changelog

All notable changes to Gunpla Fabrication Suite are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added — Milestone 1: Foundation

- Application bootstrap with `python main.py` and `python -m gunpla_fabrication_suite` entry points.
- Core infrastructure: structured logging, `platformdirs`-based data locations, typed settings
  service, SQLAlchemy engine/session management, Alembic migration coordination, a service
  container, and a synchronous/asynchronous event bus.
- Plugin SDK with a typed `PluginInterface` protocol, TOML manifests, discovery from built-in
  plugins and Python entry points, dependency resolution, and per-plugin failure isolation.
- PySide6 application shell: navigation rail, workspace stack, inspector panel, status bar,
  command palette foundation, dark theme, and persisted window geometry.
- Plugin Manager page showing plugin name, version, author, status, health, dependencies,
  permissions, and enabled state.
- `dashboard` plugin (example) and `kit_library` plugin (create/edit/list/archive kits backed by
  a real repository and service layer over SQLite).
- `scripts/release.py` versioning and release tool.

[Unreleased]: https://github.com/adeptus-craftmatica/gunpla-fabrication-suite/commits/main
