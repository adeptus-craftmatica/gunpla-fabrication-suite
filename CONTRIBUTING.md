# Contributing to Gunpla Fabrication Suite

Thanks for your interest in improving Gunpla Fabrication Suite. This project favors small,
well-scoped, well-tested changes over large speculative ones.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Before opening a pull request

Run the full validation script and make sure it passes:

```bash
python scripts/validate.py
```

This runs, in order: `ruff check`, `ruff format --check`, `mypy src`, and `pytest`.

## Architectural rules

These are enforced by review, not just convention:

- **Core stays generic.** `gunpla_fabrication_suite.core` and `gunpla_fabrication_suite.shell`
  must never contain Gunpla-domain logic (kits, builds, commissions, paints, etc.). That logic
  belongs in plugins.
- **Plugins own their vertical slice.** A plugin owns its models, migrations, repositories,
  services, UI, and tests. A plugin must never import another plugin's internal modules or touch
  another plugin's database tables directly — use the event bus or a published service interface.
- **No SQL or business logic in Qt widgets.** Widgets call services; services call repositories;
  repositories talk to the database.
- **No blocking work on the UI thread.** Network calls and image processing run through the
  background job manager (`gunpla_fabrication_suite.core.jobs`).
- **Type hints and docstrings.** Public classes and methods need type hints and a docstring
  describing intent, not restating the signature.

## Adding a new official plugin

1. Create `src/gunpla_fabrication_suite/plugins/<plugin_id>/`.
2. Add a `manifest.toml` describing the plugin's identity, dependencies, and permissions.
3. Implement a class satisfying `gunpla_fabrication_suite.plugin_sdk.PluginInterface`.
4. Register the plugin as a built-in in
   `gunpla_fabrication_suite.core.plugins.discovery.BUILTIN_PLUGIN_MODULES`.
5. Add unit tests under `tests/unit/plugins/<plugin_id>/`.

## Commit and PR etiquette

- Keep commits focused; explain *why*, not just *what*, in the commit body when it isn't obvious.
- Add or update tests for behavioral changes.
- Update `CHANGELOG.md` under `[Unreleased]` for user-visible changes.

## Reporting issues

Open an issue on the GitHub repository with reproduction steps, your OS, and the contents of
the Diagnostics window (Help → Diagnostics) where relevant.
