"""The Build Planner plugin: tracks a kit from planning through completion.

Scope for this milestone, deliberately: stages and tasks are flat (no task
dependency graphs or sub-checklists), materials/tools lists are deferred to
the Inventory plugin, photo attachments are deferred to the Photography
plugin, and templates are built-in starting points (see ``templates.py``)
rather than a user-editable database table — once a build is created, its
stages are real, per-project rows the user can reorder, add to, or remove.

This plugin depends on ``kit_library`` and resolves its ``KitService``
through the shared :class:`~gunpla_fabrication_suite.core.services.ServiceContainer`
rather than importing kit_library's internals directly.
"""

from __future__ import annotations
