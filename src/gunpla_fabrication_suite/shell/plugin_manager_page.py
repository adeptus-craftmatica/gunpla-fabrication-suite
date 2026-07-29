"""The Plugin Manager page: what's installed, its health, and enable/disable control."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gunpla_fabrication_suite.core.plugins import PluginManager, PluginRecord, PluginStatus
from gunpla_fabrication_suite.core.settings import SettingsService
from gunpla_fabrication_suite.themes import PALETTE

_COLUMNS = (
    "Name",
    "Version",
    "Author",
    "Status",
    "Health",
    "Dependencies",
    "Permissions",
    "Enabled",
)

_STATUS_SYMBOL = {
    PluginStatus.STARTED: "●",
    PluginStatus.FAILED: "✕",
    PluginStatus.DISABLED: "◌",
}


class PluginManagerPage(QWidget):
    """Lists every discovered plugin with its status, health, and controls."""

    def __init__(
        self,
        plugin_manager: PluginManager,
        settings_service: SettingsService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._plugin_manager = plugin_manager
        self._settings_service = settings_service

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QLabel("Plugin Manager")
        header.setStyleSheet("font-size: 20px; font-weight: 600;")
        layout.addWidget(header)

        self._restart_notice = QLabel(
            "Changes to enabled plugins take effect after restarting the application."
        )
        self._restart_notice.setStyleSheet(f"color: {PALETTE.text_secondary};")
        self._restart_notice.hide()
        layout.addWidget(self._restart_notice)

        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(_COLUMNS)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

        self.refresh()

    def refresh(self) -> None:
        """Repopulate the table from the plugin manager's current records."""
        records = self._plugin_manager.records
        self._table.setRowCount(len(records))

        for row, record in enumerate(records):
            manifest = record.manifest
            self._table.setItem(row, 0, QTableWidgetItem(manifest.name))
            self._table.setItem(row, 1, QTableWidgetItem(manifest.version))
            self._table.setItem(row, 2, QTableWidgetItem(manifest.author))

            status_item = QTableWidgetItem(
                f"{_STATUS_SYMBOL.get(record.status, '○')} {record.status.value.title()}"
            )
            if record.error:
                status_item.setToolTip(record.error)
            self._table.setItem(row, 3, status_item)

            self._table.setItem(row, 4, QTableWidgetItem(record.health.value.title()))
            self._table.setItem(row, 5, QTableWidgetItem(", ".join(manifest.dependencies) or "—"))
            self._table.setItem(row, 6, QTableWidgetItem(", ".join(manifest.permissions) or "—"))

            checkbox = QCheckBox()
            checkbox.setChecked(record.status != PluginStatus.DISABLED)
            checkbox.setAccessibleName(f"Enable {manifest.name}")
            checkbox.toggled.connect(
                lambda checked, plugin_id=manifest.id: self._on_toggle(plugin_id, checked)
            )
            checkbox_container = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_container)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            checkbox_layout.addWidget(checkbox)
            self._table.setCellWidget(row, 7, checkbox_container)

    def _on_toggle(self, plugin_id: str, enabled: bool) -> None:
        settings = self._settings_service.current
        disabled = set(settings.disabled_plugins)
        if enabled:
            disabled.discard(plugin_id)
        else:
            disabled.add(plugin_id)
        settings.disabled_plugins = sorted(disabled)
        self._settings_service.save(settings)
        self._restart_notice.show()

    @staticmethod
    def record_summary(record: PluginRecord) -> str:
        """A one-line human-readable summary, used in tooltips and logs."""
        return f"{record.manifest.name} v{record.manifest.version} — {record.status.value}"
