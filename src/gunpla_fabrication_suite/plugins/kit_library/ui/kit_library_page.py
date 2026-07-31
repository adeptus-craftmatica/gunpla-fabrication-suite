"""The Kit Library page: a filterable table with add/edit/archive actions."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedLayout,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gunpla_fabrication_suite.core.layout import COMMAND_DECK, LayoutManager
from gunpla_fabrication_suite.core.notifications import NotificationCenter, NotificationSeverity
from gunpla_fabrication_suite.plugins.kit_library.models.kit import CollectionStatus
from gunpla_fabrication_suite.plugins.kit_library.schemas import KitRead
from gunpla_fabrication_suite.plugins.kit_library.services.kit_service import (
    KitNotFoundError,
    KitService,
)
from gunpla_fabrication_suite.plugins.kit_library.ui.kit_dialog import KitFormDialog
from gunpla_fabrication_suite.shared_ui import (
    Card,
    EmptyStateWidget,
    InspectorPanel,
    PageHeader,
    configure_table_columns,
    confirm_destructive_action,
    set_button_kind,
    set_label_role,
)
from gunpla_fabrication_suite.themes import PALETTE

_COLUMNS = ("Name", "Manufacturer", "Grade", "Status", "Priority", "Price", "Storage Location")
_BOARD_COLUMNS = (
    CollectionStatus.WISHLIST,
    CollectionStatus.PREORDERED,
    CollectionStatus.ORDERED,
    CollectionStatus.IN_TRANSIT,
    CollectionStatus.OWNED_SEALED,
    CollectionStatus.OPENED,
)


def _build_kit_detail_widget(kit: KitRead) -> QWidget:
    """A standalone widget summarizing ``kit``, for the shared Inspector panel."""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)

    name_label = QLabel(kit.name)
    set_label_role(name_label, "section-title")
    layout.addWidget(name_label)

    subtitle_label = QLabel(f"{kit.manufacturer} — {kit.grade}")
    set_label_role(subtitle_label, "secondary")
    layout.addWidget(subtitle_label)

    layout.addSpacing(8)
    status_text = kit.status.replace("_", " ").title()
    if kit.is_deleted:
        status_text = f"Archived — {status_text}"
    price = f"${kit.purchase_price_cents / 100:.2f}" if kit.purchase_price_cents else "—"
    for title, value in (
        ("Status", status_text),
        ("Series", kit.series or "—"),
        ("Priority", str(kit.priority)),
        ("Price", price),
        ("Storage Location", kit.storage_location or "—"),
        ("Tags", ", ".join(kit.tags) or "None"),
        ("Notes", kit.notes or "None"),
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


class KitLibraryPage(QWidget):
    """Lists kits and lets the user add, edit, archive, and restore them."""

    def __init__(
        self,
        service: KitService,
        notifications: NotificationCenter,
        layout_manager: LayoutManager,
        inspector: InspectorPanel,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._notifications = notifications
        self._layout_manager = layout_manager
        self._inspector = inspector
        self._kits: list[KitRead] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)

        add_button = QPushButton("Add Kit")
        set_button_kind(add_button, "primary")
        add_button.clicked.connect(self._on_add)
        outer.addWidget(PageHeader("Kit Library", actions=[add_button]))

        toolbar_row = QHBoxLayout()
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Filter by name, manufacturer, or series…")
        self._search_edit.textChanged.connect(self._refresh_view)
        toolbar_row.addWidget(self._search_edit, stretch=1)

        self._board_checkbox = QCheckBox("Board view")
        # Command Deck defaults to the board — its wide, rail-free layout
        # suits a status overview; Rail defaults to the table. Either can
        # still be toggled manually regardless of which layout is active.
        self._board_checkbox.setChecked(layout_manager.current == COMMAND_DECK)
        self._board_checkbox.toggled.connect(self._refresh_view)
        toolbar_row.addWidget(self._board_checkbox)

        self._show_archived_checkbox = QCheckBox("Show archived")
        self._show_archived_checkbox.toggled.connect(self._reload)
        toolbar_row.addWidget(self._show_archived_checkbox)

        self._edit_button = QPushButton("Edit")
        set_button_kind(self._edit_button, "secondary")
        self._edit_button.setEnabled(False)
        self._edit_button.clicked.connect(self._on_edit)
        toolbar_row.addWidget(self._edit_button)

        self._archive_button = QPushButton("Archive")
        set_button_kind(self._archive_button, "danger")
        self._archive_button.setEnabled(False)
        self._archive_button.clicked.connect(self._on_archive)
        toolbar_row.addWidget(self._archive_button)

        self._restore_button = QPushButton("Restore")
        set_button_kind(self._restore_button, "secondary")
        self._restore_button.setEnabled(False)
        self._restore_button.clicked.connect(self._on_restore)
        toolbar_row.addWidget(self._restore_button)

        outer.addLayout(toolbar_row)

        stack_container = QWidget()
        self._stack = QStackedLayout(stack_container)

        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(_COLUMNS)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.itemSelectionChanged.connect(self._update_action_buttons)
        self._table.itemDoubleClicked.connect(lambda _item: self._on_edit())
        self._stack.addWidget(self._table)

        self._board_scroll = QScrollArea()
        self._board_scroll.setWidgetResizable(True)
        self._board_scroll.setStyleSheet("QScrollArea { border: none; }")
        self._stack.addWidget(self._board_scroll)

        self._empty_state = EmptyStateWidget(
            title="Your backlog is empty",
            description="Add the first kit in your collection or backlog to get started.",
            action_label="Add Kit",
            on_action=self._on_add,
        )
        self._stack.addWidget(self._empty_state)

        card = Card()
        card.add_widget(stack_container, stretch=1)
        outer.addWidget(card, 1)

        layout_manager.layout_changed.connect(self._on_layout_changed)
        self._reload()

    def _on_layout_changed(self, layout_id: str) -> None:
        self._board_checkbox.setChecked(layout_id == COMMAND_DECK)

    def _reload(self) -> None:
        self._kits = self._service.list_kits(
            include_archived=self._show_archived_checkbox.isChecked()
        )
        self._refresh_view()

    def _visible_kits(self) -> list[KitRead]:
        query = self._search_edit.text().strip().lower()
        return [
            kit
            for kit in self._kits
            if not query
            or query in kit.name.lower()
            or query in kit.manufacturer.lower()
            or query in (kit.series or "").lower()
        ]

    def _refresh_view(self) -> None:
        if not self._kits:
            self._table.setRowCount(0)
            self._stack.setCurrentWidget(self._empty_state)
            return

        if self._board_checkbox.isChecked():
            self._stack.setCurrentWidget(self._board_scroll)
            self._build_board()
        else:
            self._stack.setCurrentWidget(self._table)
            self._build_table()

    def _build_table(self) -> None:
        visible = self._visible_kits()
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

        configure_table_columns(self._table, stretch_column=6)
        self._update_action_buttons()

    def _build_board(self) -> None:
        content = QWidget()
        grid = QGridLayout(content)
        grid.setSpacing(12)

        visible = self._visible_kits()
        for column, status in enumerate(_BOARD_COLUMNS):
            column_widget = self._build_board_column(status, visible)
            grid.addWidget(column_widget, 0, column)

        self._board_scroll.setWidget(content)

    def _build_board_column(self, status: CollectionStatus, kits: list[KitRead]) -> QWidget:
        column = QWidget()
        # Background/border come from the #kanbanColumn rule in
        # themes/base.py's global stylesheet, so they stay correct across a
        # live theme switch.
        column.setObjectName("kanbanColumn")
        column.setFixedWidth(220)
        layout = QVBoxLayout(column)

        label = QLabel(status.value.replace("_", " ").title())
        set_label_role(label, "section-title")
        layout.addWidget(label)

        matching = [kit for kit in kits if kit.status == status.value and not kit.is_deleted]
        for kit in matching:
            layout.addWidget(self._build_board_card(kit))
        layout.addStretch(1)
        return column

    def _build_board_card(self, kit: KitRead) -> QWidget:
        card = QPushButton(f"{kit.name}\n{kit.manufacturer} — {kit.grade}")
        # Styled via the #kanbanCard rule in themes/base.py's global
        # stylesheet — see _build_board_column's comment.
        card.setObjectName("kanbanCard")
        card.clicked.connect(lambda: self._edit_kit(kit))
        return card

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

        # The shared Inspector panel is relevant regardless of which layout
        # is active — Rail and Command Deck just collapse it to 0 width by
        # default, but a user can still drag it open manually. Board view
        # has no equivalent "selected" state (cards open the edit dialog
        # directly), so only the table drives this.
        self._inspector.set_details_widget(
            _build_kit_detail_widget(kit) if kit is not None else None
        )

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
        self._edit_kit(kit)

    def _edit_kit(self, kit: KitRead) -> None:
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
