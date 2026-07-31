"""The Plugin Manager page: what's installed, its health, and enable/disable control."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gunpla_fabrication_suite.core.layout import COMMAND_DECK, LayoutManager
from gunpla_fabrication_suite.core.plugins import PluginManager, PluginRecord, PluginStatus
from gunpla_fabrication_suite.core.settings import SettingsService
from gunpla_fabrication_suite.shared_ui import (
    Card,
    InspectorPanel,
    PageHeader,
    configure_table_columns,
    set_label_role,
)
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


def _build_plugin_detail_widget(record: PluginRecord) -> QWidget:
    """A standalone widget summarizing ``record``, for the shared Inspector panel.

    Built fresh per selection rather than reusing persistent labels — unlike
    the embedded Command Deck detail card, this widget is handed off to
    ``InspectorPanel.set_details_widget()``, which owns and tears it down
    itself.
    """
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)

    manifest = record.manifest
    name_label = QLabel(manifest.name)
    set_label_role(name_label, "section-title")
    layout.addWidget(name_label)

    subtitle_label = QLabel(
        f"v{manifest.version} by {manifest.author or 'Unknown'} — {record.status.value.title()}"
    )
    set_label_role(subtitle_label, "secondary")
    layout.addWidget(subtitle_label)

    layout.addSpacing(8)
    description_label = QLabel(manifest.description or "No description provided.")
    description_label.setWordWrap(True)
    layout.addWidget(description_label)

    layout.addSpacing(8)
    for title, value in (
        ("Dependencies", ", ".join(manifest.dependencies) or "None"),
        ("Optional Dependencies", ", ".join(manifest.optional_dependencies) or "None"),
        ("Permissions", ", ".join(manifest.permissions) or "None"),
        ("Error", record.error or "None"),
    ):
        title_label = QLabel(title)
        set_label_role(title_label, "section-title")
        layout.addWidget(title_label)
        value_label = QLabel(value)
        value_label.setWordWrap(True)
        set_label_role(value_label, "secondary")
        layout.addWidget(value_label)

    layout.addStretch(1)
    return widget


class PluginManagerPage(QWidget):
    """Lists every discovered plugin with its status, health, and controls."""

    def __init__(
        self,
        plugin_manager: PluginManager,
        settings_service: SettingsService,
        layout_manager: LayoutManager,
        inspector: InspectorPanel,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._plugin_manager = plugin_manager
        self._settings_service = settings_service
        self._layout_manager = layout_manager
        self._inspector = inspector
        self._records: Sequence[PluginRecord] = ()

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(24, 24, 24, 24)
        self._layout.setSpacing(12)

        self._layout.addWidget(PageHeader("Plugin Manager"))

        self._restart_notice = QLabel(
            "Changes to enabled plugins take effect after restarting the application."
        )
        self._restart_notice.setStyleSheet(f"color: {PALETTE.text_secondary};")
        self._restart_notice.hide()
        self._layout.addWidget(self._restart_notice)

        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(_COLUMNS)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.itemSelectionChanged.connect(self._update_detail_panel)

        self._detail_card = self._build_detail_card()

        self._body_container: QWidget | None = None
        self._rebuild_body(layout_manager.current)

        layout_manager.layout_changed.connect(self._on_layout_changed)
        self.refresh()

    def _build_detail_card(self) -> Card:
        card = Card("Plugin Details")

        self._detail_placeholder = QLabel("Select a plugin to see its full details here.")
        set_label_role(self._detail_placeholder, "secondary")
        card.add_widget(self._detail_placeholder)

        self._detail_content = QWidget()
        detail_layout = QVBoxLayout(self._detail_content)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(4)

        self._detail_name = QLabel()
        set_label_role(self._detail_name, "section-title")
        detail_layout.addWidget(self._detail_name)

        self._detail_subtitle = QLabel()
        set_label_role(self._detail_subtitle, "secondary")
        detail_layout.addWidget(self._detail_subtitle)

        detail_layout.addSpacing(8)

        self._detail_description = QLabel()
        self._detail_description.setWordWrap(True)
        detail_layout.addWidget(self._detail_description)

        detail_layout.addSpacing(8)
        self._detail_dependencies = self._add_detail_field(detail_layout, "Dependencies")
        self._detail_optional = self._add_detail_field(detail_layout, "Optional Dependencies")
        self._detail_permissions = self._add_detail_field(detail_layout, "Permissions")
        self._detail_error = self._add_detail_field(detail_layout, "Error")
        detail_layout.addStretch(1)

        card.add_widget(self._detail_content, stretch=1)
        self._detail_content.hide()
        return card

    def _add_detail_field(self, layout: QVBoxLayout, title: str) -> QLabel:
        title_label = QLabel(title)
        set_label_role(title_label, "section-title")
        layout.addWidget(title_label)
        value_label = QLabel()
        value_label.setWordWrap(True)
        set_label_role(value_label, "secondary")
        layout.addWidget(value_label)
        return value_label

    def _on_layout_changed(self, layout_id: str) -> None:
        self._rebuild_body(layout_id)

    def _rebuild_body(self, layout_id: str) -> None:
        """Rebuild only the table/detail arrangement, reusing the live table.

        Command Deck's extra width — no left nav rail eating into it — is
        used for a permanent detail panel next to the table instead of
        forcing tooltips to explain truncated dependency/permission lists.
        """
        old_body = self._body_container
        if old_body is not None:
            self._layout.removeWidget(old_body)
            old_body.setParent(None)
            old_body.deleteLater()

        # _detail_card only ends up back in the new body below when
        # layout_id == COMMAND_DECK — for every other layout it must still
        # be detached from the outgoing body first, or it gets destroyed
        # right along with it (deleteLater() takes its whole child tree
        # with it), taking out the *next* switch back to Command Deck with
        # a dead widget. Same bug class already fixed for MainWindow's nav
        # widgets and the shared Inspector.
        self._detail_card.setParent(None)

        if layout_id == COMMAND_DECK:
            splitter = QSplitter()
            table_card = Card()
            table_card.add_widget(self._table, stretch=1)
            splitter.addWidget(table_card)
            splitter.addWidget(self._detail_card)
            splitter.setStretchFactor(0, 1)
            splitter.setSizes([700, 320])
            body: QWidget = splitter
        else:
            card = Card()
            card.add_widget(self._table, stretch=1)
            body = card

        self._body_container = body
        self._layout.addWidget(body, 1)
        # setParent(None) above hide()-cascades down through the outgoing
        # body's descendants — the reused, live table (and the detail card,
        # under Command Deck) must be shown again explicitly or they render
        # as empty space. See build_detail_view.py for the same pattern.
        self._table.show()
        self._detail_card.show()
        self._update_detail_panel()

    def _selected_record(self) -> PluginRecord | None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._records):
            return None
        return self._records[row]

    def _update_detail_panel(self) -> None:
        record = self._selected_record()

        # The shared Inspector panel is relevant regardless of which layout
        # is active — Rail and Command Deck just collapse it to 0 width by
        # default, but a user can still drag it open manually.
        self._inspector.set_details_widget(
            _build_plugin_detail_widget(record) if record is not None else None
        )

        if self._layout_manager.current != COMMAND_DECK:
            return

        if record is None:
            self._detail_placeholder.show()
            self._detail_content.hide()
            return

        self._detail_placeholder.hide()
        self._detail_content.show()

        manifest = record.manifest
        self._detail_name.setText(manifest.name)
        self._detail_subtitle.setText(
            f"v{manifest.version} by {manifest.author or 'Unknown'} — {record.status.value.title()}"
        )
        self._detail_description.setText(manifest.description or "No description provided.")
        self._detail_dependencies.setText(", ".join(manifest.dependencies) or "None")
        self._detail_optional.setText(", ".join(manifest.optional_dependencies) or "None")
        self._detail_permissions.setText(", ".join(manifest.permissions) or "None")
        self._detail_error.setText(record.error or "None")

    def refresh(self) -> None:
        """Repopulate the table from the plugin manager's current records."""
        self._records = self._plugin_manager.records
        self._table.setRowCount(len(self._records))

        for row, record in enumerate(self._records):
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

        configure_table_columns(self._table, stretch_column=0, tooltip_columns=(5, 6))
        self._update_detail_panel()

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
