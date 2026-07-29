"""The Kit Library page: a filterable table with add/edit/archive actions."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedLayout,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gunpla_fabrication_suite.core.notifications import NotificationCenter, NotificationSeverity
from gunpla_fabrication_suite.plugins.kit_library.schemas import KitRead
from gunpla_fabrication_suite.plugins.kit_library.services.kit_service import (
    KitNotFoundError,
    KitService,
)
from gunpla_fabrication_suite.plugins.kit_library.ui.kit_dialog import KitFormDialog
from gunpla_fabrication_suite.shared_ui import EmptyStateWidget, confirm_destructive_action
from gunpla_fabrication_suite.themes import PALETTE

_COLUMNS = ("Name", "Manufacturer", "Grade", "Status", "Priority", "Price", "Storage Location")


class KitLibraryPage(QWidget):
    """Lists kits and lets the user add, edit, archive, and restore them."""

    def __init__(
        self,
        service: KitService,
        notifications: NotificationCenter,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._notifications = notifications
        self._kits: list[KitRead] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)

        header_row = QHBoxLayout()
        title = QLabel("Kit Library")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        header_row.addWidget(title)
        header_row.addStretch(1)

        add_button = QPushButton("Add Kit")
        add_button.setDefault(True)
        add_button.clicked.connect(self._on_add)
        header_row.addWidget(add_button)
        outer.addLayout(header_row)

        toolbar_row = QHBoxLayout()
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Filter by name, manufacturer, or series…")
        self._search_edit.textChanged.connect(self._refresh_table)
        toolbar_row.addWidget(self._search_edit, stretch=1)

        self._show_archived_checkbox = QCheckBox("Show archived")
        self._show_archived_checkbox.toggled.connect(self._reload)
        toolbar_row.addWidget(self._show_archived_checkbox)

        self._edit_button = QPushButton("Edit")
        self._edit_button.setEnabled(False)
        self._edit_button.clicked.connect(self._on_edit)
        toolbar_row.addWidget(self._edit_button)

        self._archive_button = QPushButton("Archive")
        self._archive_button.setEnabled(False)
        self._archive_button.clicked.connect(self._on_archive)
        toolbar_row.addWidget(self._archive_button)

        self._restore_button = QPushButton("Restore")
        self._restore_button.setEnabled(False)
        self._restore_button.clicked.connect(self._on_restore)
        toolbar_row.addWidget(self._restore_button)

        outer.addLayout(toolbar_row)

        self._stack = QStackedLayout()
        outer.addLayout(self._stack, stretch=1)

        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(_COLUMNS)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.itemSelectionChanged.connect(self._update_action_buttons)
        self._table.itemDoubleClicked.connect(lambda _item: self._on_edit())
        self._stack.addWidget(self._table)

        self._empty_state = EmptyStateWidget(
            title="Your backlog is empty",
            description="Add the first kit in your collection or backlog to get started.",
            action_label="Add Kit",
            on_action=self._on_add,
        )
        self._stack.addWidget(self._empty_state)

        self._reload()

    def _reload(self) -> None:
        self._kits = self._service.list_kits(
            include_archived=self._show_archived_checkbox.isChecked()
        )
        self._refresh_table()

    def _refresh_table(self) -> None:
        query = self._search_edit.text().strip().lower()
        visible = [
            kit
            for kit in self._kits
            if not query
            or query in kit.name.lower()
            or query in kit.manufacturer.lower()
            or query in (kit.series or "").lower()
        ]

        if not self._kits:
            self._table.setRowCount(0)
            self._stack.setCurrentWidget(self._empty_state)
            return
        self._stack.setCurrentWidget(self._table)

        self._table.setRowCount(len(visible))
        for row, kit in enumerate(visible):
            self._table.setItem(row, 0, self._make_item(kit, kit.name))
            self._table.setItem(row, 1, self._make_item(kit, kit.manufacturer))
            self._table.setItem(row, 2, self._make_item(kit, kit.grade))

            status_text = kit.status.replace("_", " ").title()
            if kit.is_deleted:
                status_text = f"Archived — {status_text}"
            self._table.setItem(row, 3, self._make_item(kit, status_text))

            self._table.setItem(row, 4, self._make_item(kit, str(kit.priority)))
            price = f"${kit.purchase_price_cents / 100:.2f}" if kit.purchase_price_cents else "—"
            self._table.setItem(row, 5, self._make_item(kit, price))
            self._table.setItem(row, 6, self._make_item(kit, kit.storage_location or "—"))

        self._update_action_buttons()

    def _make_item(self, kit: KitRead, text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, kit)
        if kit.is_deleted:
            item.setForeground(QColor(PALETTE.text_disabled))
        return item

    def _selected_kit(self) -> KitRead | None:
        items = self._table.selectedItems()
        if not items:
            return None
        data = items[0].data(Qt.ItemDataRole.UserRole)
        assert isinstance(data, KitRead)
        return data

    def _update_action_buttons(self) -> None:
        kit = self._selected_kit()
        self._edit_button.setEnabled(kit is not None)
        self._archive_button.setEnabled(kit is not None and not kit.is_deleted)
        self._restore_button.setEnabled(kit is not None and kit.is_deleted)

    def _on_add(self) -> None:
        dialog = KitFormDialog(parent=self)
        accepted = dialog.exec() == KitFormDialog.DialogCode.Accepted
        data = dialog.result_data()
        if accepted and data is not None:
            self._service.create_kit(data)
            self._notifications.post(
                "Kit added to your collection.",
                severity=NotificationSeverity.SUCCESS,
                source="kit_library",
            )
            self._reload()

    def _on_edit(self) -> None:
        kit = self._selected_kit()
        if kit is None:
            return
        dialog = KitFormDialog(existing=kit, parent=self)
        accepted = dialog.exec() == KitFormDialog.DialogCode.Accepted
        data = dialog.result_data()
        if accepted and data is not None:
            try:
                self._service.update_kit(kit.id, data)
            except KitNotFoundError:
                QMessageBox.warning(self, "Kit not found", "This kit no longer exists.")
            else:
                self._notifications.post(
                    "Kit updated.", severity=NotificationSeverity.SUCCESS, source="kit_library"
                )
            self._reload()

    def _on_archive(self) -> None:
        kit = self._selected_kit()
        if kit is None:
            return
        if not confirm_destructive_action(
            self,
            title="Archive kit",
            message=f"Archive '{kit.name}'? It will be hidden from the active list until restored.",
            confirm_label="Archive",
        ):
            return
        self._service.archive_kit(kit.id)
        self._notifications.post(
            f"'{kit.name}' archived.", severity=NotificationSeverity.INFO, source="kit_library"
        )
        self._reload()

    def _on_restore(self) -> None:
        kit = self._selected_kit()
        if kit is None:
            return
        self._service.restore_kit(kit.id)
        self._notifications.post(
            f"'{kit.name}' restored.", severity=NotificationSeverity.SUCCESS, source="kit_library"
        )
        self._reload()
