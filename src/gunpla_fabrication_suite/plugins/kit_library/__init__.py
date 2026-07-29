"""The Kit Library plugin: personal collection and backlog management.

Schema migrations for this plugin's tables live in the repository-wide
``migrations/versions/`` directory rather than inside this package. Alembic
maintains one linear revision history per SQLite database; a per-plugin
migrations folder would require multi-head branch merging for no real
benefit at this stage. The model modules below are what get imported to
register this plugin's tables — see
``gunpla_fabrication_suite.core.plugins.discovery.MODEL_MODULES``.
"""

from __future__ import annotations
