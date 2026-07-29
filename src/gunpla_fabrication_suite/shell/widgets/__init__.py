"""Reusable shell chrome widgets: the workspace stack, inspector, and status bar."""

from __future__ import annotations

from gunpla_fabrication_suite.shell.widgets.inspector import InspectorPanel
from gunpla_fabrication_suite.shell.widgets.status_bar import AppStatusBar
from gunpla_fabrication_suite.shell.widgets.workspace import WorkspaceStack

__all__ = ["AppStatusBar", "InspectorPanel", "WorkspaceStack"]
