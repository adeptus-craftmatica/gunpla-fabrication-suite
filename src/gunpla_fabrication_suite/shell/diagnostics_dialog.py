"""The Diagnostics window: a snapshot of environment and application health."""

from __future__ import annotations

import platform
import sys

from PySide6 import __version__ as pyside_version
from PySide6.QtWidgets import QDialog, QLabel, QPlainTextEdit, QVBoxLayout, QWidget

from gunpla_fabrication_suite import __version__
from gunpla_fabrication_suite.core.paths import ApplicationPaths
from gunpla_fabrication_suite.core.persistence import DatabaseService
from gunpla_fabrication_suite.core.plugins import PluginManager


class DiagnosticsDialog(QDialog):
    """A read-only report of versions, data locations, and plugin/database health."""

    def __init__(
        self,
        *,
        paths: ApplicationPaths,
        database: DatabaseService,
        plugin_manager: PluginManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Diagnostics")
        self.resize(560, 480)

        layout = QVBoxLayout(self)
        title = QLabel("Diagnostics")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title)

        text = QPlainTextEdit()
        text.setReadOnly(True)
        text.setPlainText(self._build_report(paths, database, plugin_manager))
        layout.addWidget(text)

    def _build_report(
        self, paths: ApplicationPaths, database: DatabaseService, plugin_manager: PluginManager
    ) -> str:
        integrity_ok = database.check_integrity()
        lines = [
            f"Gunpla Fabrication Suite   {__version__}",
            f"Python                     {sys.version.split()[0]}",
            f"PySide6 (Qt)               {pyside_version}",
            f"Operating System           {platform.platform()}",
            "",
            "Data directories",
            f"  Root                     {paths.root}",
            f"  Database                 {paths.database_file}",
            f"  Media                    {paths.media_dir}",
            f"  Logs                     {paths.logs_dir}",
            f"  Backups                  {paths.backups_dir}",
            f"  Plugins (user)           {paths.plugins_dir}",
            "",
            f"Database integrity check   {'OK' if integrity_ok else 'FAILED'}",
            "",
            "Plugins",
        ]
        for record in plugin_manager.records:
            line = (
                f"  {record.manifest.name:<24} v{record.manifest.version:<10} {record.status.value}"
            )
            if record.error:
                line += f"  ({record.error})"
            lines.append(line)

        return "\n".join(lines)
