# Architecture Overview

Gunpla Fabrication Suite is a plugin-first desktop application. The core provides
infrastructure only; every Gunpla-domain feature is implemented as an isolated plugin.

## Layers

```text
┌─────────────────────────────────────────────────────────────┐
│ plugins/            Gunpla-domain features (kit_library, ...) │
├─────────────────────────────────────────────────────────────┤
│ plugin_sdk/         the surface plugins are built against     │
├─────────────────────────────────────────────────────────────┤
│ shell/              main window, navigation, command palette  │
│ shared_ui/, themes/ reusable widgets and the visual theme      │
├─────────────────────────────────────────────────────────────┤
│ application/        bootstrap: wires everything together      │
├─────────────────────────────────────────────────────────────┤
│ core/               generic infrastructure (see below)        │
└─────────────────────────────────────────────────────────────┘
```

Dependencies only point downward: `plugins` depends on `plugin_sdk`; `plugin_sdk` and `shell`
depend on `core`; `core` depends on nothing else in this package. A plugin must never import
`gunpla_fabrication_suite.core` or another plugin's internal modules directly.

## `core/` responsibilities

- **`core.paths`** — resolves OS-appropriate data directories via `platformdirs`. No module
  anywhere else hardcodes a filesystem path.
- **`core.logging`** — structured logging (structlog + stdlib), writing to the managed logs
  directory.
- **`core.settings`** — a typed, Pydantic-validated settings document persisted as JSON.
- **`core.persistence`** — the SQLAlchemy engine/session (`DatabaseService`), the shared
  declarative `Base` and column mixins (`UUIDPrimaryKeyMixin`, `TimestampMixin`,
  `SoftDeleteMixin`, `VersionMixin`), and programmatic Alembic migration coordination.
- **`core.events`** — `EventBus`, a typed publish/subscribe bus. A handler that raises is logged
  and isolated; it never blocks other handlers or the publisher.
- **`core.services`** — `ServiceContainer`, an explicit (no reflection) dependency registry.
- **`core.plugins`** — discovery (built-in packages, the user plugin directory, and
  `gunpla_fabrication_suite.plugins` entry points), dependency-ordered loading, and per-plugin
  failure isolation.
- **`core.notifications`** — `NotificationCenter`, the source of non-blocking toast
  notifications.
- **`core.jobs`** — `BackgroundJobManager`, running work on a Qt thread pool with progress
  reporting so the UI thread never blocks.

## The plugin contract

A plugin is a Python package with a `manifest.toml` (id, version, `api_version`, entry point,
dependencies, permissions) and a class implementing
`gunpla_fabrication_suite.plugin_sdk.PluginInterface`:

```text
register(context)   -> wire up navigation/dashboard/command contributions; no I/O
initialize()        -> construct repositories and services
start()              -> begin normal operation (e.g. subscribe to events)
stop()               -> pause background activity, keep state
shutdown()           -> release all resources
```

`PluginManager` calls these in order for every discovered plugin, topologically sorted by
`manifest.dependencies`. If any step raises, that plugin is marked `FAILED`, a notification is
posted, its partial contributions are rolled back, and every other plugin keeps loading — a
single plugin can never take down the application.

Contribution points currently implemented: navigation pages, dashboard widgets, and
command-palette commands, via `NavigationRegistry`, `DashboardWidgetRegistry`, and
`CommandRegistry` in `plugin_sdk.registries`. More contribution types (settings pages, importers,
exporters, reports, search providers, automation triggers/actions, image processors) will be
added alongside the milestones that consume them.

## Persistence

All plugins share one SQLite database and one Alembic revision history (`migrations/`), so a
single `PRAGMA foreign_keys=ON` and one linear upgrade path cover the whole application. A
plugin still *owns* its tables in the sense that only its own repository queries them — nothing
elsewhere issues SQL against another plugin's tables. New migrations are written by hand (or via
`alembic revision --autogenerate` after importing the relevant model module) into
`migrations/versions/`; `core.plugins.discovery.MODEL_MODULES` lists which plugin model modules
must be imported for autogenerate to see their tables.

Money is stored as integer cents, never floating point. Timestamps are timezone-aware UTC
internally, formatted for the user's locale in the UI layer.

## Events

Plugins communicate through typed, immutable `@dataclass(frozen=True, slots=True)` events rather
than importing each other's internals — for example, `kit_library.events.KitAdded`. A plugin
that wants to react to another plugin's changes subscribes to its events; it never touches its
repository or ORM models.

## UI shell

`shell.MainWindow` composes, but does not implement, its pieces: `NavigationRail` (built from
`NavigationRegistry`), `WorkspaceStack` (lazily builds each page's widget on first visit),
`InspectorPanel` (a generic, reusable right-hand panel), and `AppStatusBar` (database, jobs,
notifications, plugin health — each shown with both an icon and text, never color alone). The
command palette (`Ctrl+K`) fuzzy-matches every registered `CommandContribution`.

## Milestones

Milestone 1 (this foundation) delivers: the shell, plugin SDK, plugin manager, event bus, service
container, SQLite + Alembic, logging, settings persistence, the Dashboard plugin, and a fully
working Kit Library plugin. Subsequent milestones (Build Planner, Photography, Catalog Import,
Commissions, Inventory & Finance, Calendar/Portfolio/Reporting/Automation) each add one or more
plugins without changing this core.
