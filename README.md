# Gunpla Fabrication Suite

A premium, offline-first workshop management application for Gunpla builders — track your kit
collection and backlog, plan and log builds, manage commissions and customers, and keep tabs on
paints, supplies, and finances, all from one desktop app.

> **Status:** early foundation (Milestones 1 and 3). The core plugin architecture, application
> shell, Kit Library, and Build Planner are implemented; most other domain plugins described in
> [`docs/architecture.md`](docs/architecture.md) are not yet built.

## Screenshots

_Coming soon._

## Features

- **Plugin-first architecture** — every major feature (Kit Library, Build Planner, Commissions,
  Inventory, ...) is an isolated plugin that owns its own models, migrations, services, and UI.
  Plugin failures are isolated and never crash the application.
- **Kit Library** — track kits you own or want, with manufacturer, grade, scale, series, purchase
  details, priority, storage location, tags, and notes. Full create/edit/list/archive/restore
  workflow backed by a real SQLite database.
- **Build Planner** — turn a kit into a tracked build from one of eight templates, with
  reorderable weighted stages and tasks, a work-session timer that survives a restart, and a
  build journal. See [`docs/architecture.md`](docs/architecture.md) for how it depends on Kit
  Library through the shared service container instead of importing its internals.
- **Dashboard** — a workspace overview assembled entirely from widgets contributed by other
  plugins, including a "Continue Building" card.
- **Plugin Manager** — see every discovered plugin's version, author, status, health,
  dependencies, and permissions, and enable or disable it.
- **Command palette** (`Ctrl+K`) — fuzzy-searchable access to every registered action.
- **Dark, accessible interface** — a neutral, high-contrast theme where status is always
  communicated with more than color alone.
- **Local-first** — no account, no cloud, no telemetry. All data lives in a per-user application
  data directory on your machine.

## Installation

Requires Python 3.12 or newer.

```bash
git clone https://github.com/adeptus-craftmatica/gunpla-fabrication-suite.git
cd gunpla-fabrication-suite
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Running the application

```bash
python main.py
```

or, equivalently:

```bash
python -m gunpla_fabrication_suite
```

or, if installed as a console script:

```bash
gunpla-fabrication-suite
```

On first launch the app creates its data directory, initializes the SQLite database, and runs
any pending Alembic migrations automatically.

## Development setup

```bash
pip install -e ".[dev]"
python scripts/validate.py   # ruff check, ruff format --check, mypy, pytest
```

Individual tools:

```bash
ruff check .
ruff format --check .
mypy src
pytest
```

## Testing

```bash
pytest                # all tests
pytest tests/unit      # unit tests only
pytest tests/ui        # pytest-qt UI smoke tests
```

## Project structure

```text
gunpla-fabrication-suite/
├── src/gunpla_fabrication_suite/
│   ├── application/     # bootstrap: wires core infrastructure into a running Qt app
│   ├── core/            # generic infrastructure: plugins, persistence, events, jobs, settings...
│   ├── shell/            # main window, navigation, command palette, plugin manager UI
│   ├── plugin_sdk/       # the public surface plugin authors build against
│   ├── shared_ui/        # reusable, theme-aware widgets (toasts, empty states, confirm dialogs)
│   ├── themes/           # the dark palette and stylesheet
│   └── plugins/          # official plugins (dashboard, kit_library, ...)
├── migrations/           # Alembic environment and revision history
├── tests/{unit,integration,ui,fixtures}/
├── scripts/              # release.py, validate.py
└── main.py               # `python main.py` launcher
```

See [`docs/architecture.md`](docs/architecture.md) for the full architectural overview and
[`CONTRIBUTING.md`](CONTRIBUTING.md) for the rules enforced on every plugin.

## Plugin architecture

Plugins are discovered from three sources, in order: built-in plugins under
`gunpla_fabrication_suite.plugins`, a user plugin directory inside the managed data folder, and
Python entry points under the `gunpla_fabrication_suite.plugins` group (for future third-party
distribution). Every plugin ships a `manifest.toml` describing its id, version, dependencies, and
permissions, and implements the lifecycle in
[`gunpla_fabrication_suite.plugin_sdk.PluginInterface`](src/gunpla_fabrication_suite/plugin_sdk/interface.py)
(`register` → `initialize` → `start`, and `stop` → `shutdown`). A plugin that fails at any stage
is marked unhealthy and disabled for the session; every other plugin keeps loading. See
[`CONTRIBUTING.md`](CONTRIBUTING.md#adding-a-new-official-plugin) for how to add one.

## Data location

Gunpla Fabrication Suite stores everything locally, in an OS-appropriate per-user data directory
resolved by [`platformdirs`](https://pypi.org/project/platformdirs/):

| OS      | Location |
|---------|----------|
| Windows | `%LOCALAPPDATA%\AdeptusCraftmatica\GunplaFabricationSuite` |
| macOS   | `~/Library/Application Support/GunplaFabricationSuite` |
| Linux   | `~/.local/share/GunplaFabricationSuite` |

Inside that root: `database/` (the SQLite file), `media/` (originals, previews, thumbnails,
exports), `imports/`, `exports/`, `backups/`, `cache/`, `logs/`, `plugins/` (user plugins), and
`recovery/`. Use **Help → Diagnostics** inside the app to see the exact resolved paths on your
machine.

## Backup information

Automated backup and restore is planned but not yet implemented (see the milestone list in
`docs/architecture.md`). Until then, back up the entire data directory above — it's a complete,
self-contained snapshot of your collection, builds, and settings.

## Versioning and releases

Releases are cut with [`scripts/release.py`](scripts/release.py), which bumps the version, builds
platform installers with PyInstaller, tags the release, and pushes it to GitHub.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for development setup, architectural rules, and how to
add a new plugin. See [`SECURITY.md`](SECURITY.md) for the security and data-handling policy.

## License

[MIT](LICENSE)

## Author

**Adeptus Craftmatica**
[adeptus.craftmatica@proton.me](mailto:adeptus.craftmatica@proton.me)
