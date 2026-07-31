"""Reusable shell chrome widgets: the workspace stack and status bar.

``InspectorPanel`` used to live here too; it moved to ``shared_ui`` so
``plugin_sdk.PluginContext`` can carry a live reference to it without a
circular import (``shell`` already imports from ``plugin_sdk``). Import it
from ``gunpla_fabrication_suite.shared_ui`` instead.
"""

from __future__ import annotations

from gunpla_fabrication_suite.shell.widgets.status_bar import AppStatusBar
from gunpla_fabrication_suite.shell.widgets.workspace import WorkspaceStack

__all__ = ["AppStatusBar", "WorkspaceStack"]
