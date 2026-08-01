"""The Wishlist page: a filterable table with add/edit/purchase/archive actions."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
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
from gunpla_fabrication_suite.plugins.kit_library.models.kit import CollectionStatus
from gunpla_fabrication_suite.plugins.kit_library.schemas import KitCreate
from gunpla_fabrication_suite.plugins.kit_library.services.kit_service import KitService
from gunpla_fabrication_suite.plugins.kit_library.ui.kit_dialog import KitFormDialog
from gunpla_fabrication_suite.plugins.wishlist.models.wishlist_item import WishlistItemType
from gunpla_fabrication_suite.plugins.wishlist.schemas import WishlistItemRead
from gunpla_fabrication_suite.plugins.wishlist.services.wishlist_service import (
    WishlistItemNotFoundError,
    WishlistService,
)
from gunpla_fabrication_suite.plugins.wishlist.ui.wishlist_dialog import WishlistItemFormDialog
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

_COLUMNS = ("Name", "Type", "Manufacturer", "Priority", "Est. Price", "Status")

_ALL_TYPES = "All types"

# Placeholder grade for a Kit Library entry auto-created from a purchased
# wishlist item — WishlistItem deliberately carries no grade/scale field
# (those are Kit Library concerns), so the created Kit gets this common
# default and the user is immediately prompted to correct it.
_DEFAULT_KIT_GRADE = "HG"


def _status_text(item: WishlistItemRead) -> str:
    if item.is_deleted:
        return "Archived"
    if item.is_purchased:
        return "Purchased"
    return "Wanted"


def _build_wishlist_item_detail_widget(item: WishlistItemRead) -> QWidget:
    """A standalone widget summarizing ``item``, for the shared Inspector panel."""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)

    name_label = QLabel(item.name)
    set_label_role(name_label, "section-title")
    layout.addWidget(name_label)

    subtitle_label = QLabel(f"{item.item_type.title()} — {item.manufacturer or 'Unknown'}")
    set_label_role(subtitle_label, "secondary")
    layout.addWidget(subtitle_label)

    layout.addSpacing(8)
    price = f"${item.estimated_price_cents / 100:.2f}" if item.estimated_price_cents else "—"
    for title, value in (
        ("Priority", str(item.priority)),
        ("Estimated price", price),
        ("Status", _status_text(item)),
        ("Tags", ", ".join(item.tags) or "None"),
        ("Notes", item.notes or "None"),
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


class WishlistPage(QWidget):
    """Lists wishlist items and lets the user add, edit, purchase, archive, and restore them."""

    def __init__(
        self,
        service: WishlistService,
        kit_service: KitService,
        notifications: NotificationCenter,
        inspector: InspectorPanel,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._kit_service = kit_service
        self._notifications = notifications
        self._inspector = inspector
        self._items: list[WishlistItemRead] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)

        add_button = QPushButton("Add Item")
        set_button_kind(add_button, "primary")
        add_button.clicked.connect(self._on_add)
        outer.addWidget(PageHeader("Wishlist", actions=[add_button]))

        toolbar_row = QHBoxLayout()
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Filter by name or manufacturer…")
        self._search_edit.textChanged.connect(self._refresh_table)
        toolbar_row.addWidget(self._search_edit, stretch=1)

        self._type_combo = QComboBox()
        self._type_combo.addItem(_ALL_TYPES, None)
        for item_type in WishlistItemType:
            self._type_combo.addItem(item_type.value.title(), item_type)
        self._type_combo.currentIndexChanged.connect(self._refresh_table)
        toolbar_row.addWidget(self._type_combo)

        self._show_purchased_checkbox = QCheckBox("Show purchased")
        self._show_purchased_checkbox.toggled.connect(self._reload)
        toolbar_row.addWidget(self._show_purchased_checkbox)

        self._show_archived_checkbox = QCheckBox("Show archived")
        self._show_archived_checkbox.toggled.connect(self._reload)
        toolbar_row.addWidget(self._show_archived_checkbox)

        self._edit_button = QPushButton("Edit")
        set_button_kind(self._edit_button, "secondary")
        self._edit_button.setEnabled(False)
        self._edit_button.clicked.connect(self._on_edit)
        toolbar_row.addWidget(self._edit_button)

        self._mark_purchased_button = QPushButton("Mark Purchased")
        set_button_kind(self._mark_purchased_button, "secondary")
        self._mark_purchased_button.setEnabled(False)
        self._mark_purchased_button.clicked.connect(self._on_mark_purchased)
        toolbar_row.addWidget(self._mark_purchased_button)

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

        self._empty_state = EmptyStateWidget(
            title="Your wishlist is empty",
            description="Add kits, tools, paint, or parts you want to buy to keep track of them.",
            action_label="Add Item",
            on_action=self._on_add,
        )
        self._stack.addWidget(self._empty_state)

        card = Card()
        card.add_widget(stack_container, stretch=1)
        outer.addWidget(card, 1)

        self._reload()

    def _reload(self) -> None:
        self._items = self._service.list_items(
            include_archived=self._show_archived_checkbox.isChecked(),
            include_purchased=self._show_purchased_checkbox.isChecked(),
        )
        self._refresh_table()

    def show_item(self, item_id: str) -> None:
        """Select ``item_id`` in the table, the same as a user clicking its row."""
        self._search_edit.clear()
        self._type_combo.setCurrentIndex(0)
        target = next(
            (
                i
                for i in self._service.list_items(include_archived=True, include_purchased=True)
                if i.id == item_id
            ),
            None,
        )
        if target is not None:
            if target.is_deleted:
                self._show_archived_checkbox.setChecked(True)
            if target.is_purchased:
                self._show_purchased_checkbox.setChecked(True)
        self._reload()
        for row in range(self._table.rowCount()):
            cell = self._table.item(row, 0)
            if cell is None:
                continue
            data = cell.data(Qt.ItemDataRole.UserRole)
            if isinstance(data, WishlistItemRead) and data.id == item_id:
                self._table.selectRow(row)
                self._table.scrollToItem(cell)
                return

    def _visible_items(self) -> list[WishlistItemRead]:
        query = self._search_edit.text().strip().lower()
        item_type = self._type_combo.currentData()
        return [
            item
            for item in self._items
            if (
                not query
                or query in item.name.lower()
                or query in (item.manufacturer or "").lower()
            )
            and (item_type is None or item.item_type == item_type)
        ]

    def _refresh_table(self) -> None:
        if not self._items:
            self._table.setRowCount(0)
            self._stack.setCurrentWidget(self._empty_state)
            return
        self._stack.setCurrentWidget(self._table)

        visible = self._visible_items()
        self._table.setRowCount(len(visible))
        for row, item in enumerate(visible):
            self._set_row_item(row, 0, item.name, item)
            self._set_row_item(row, 1, item.item_type.title(), item)
            self._set_row_item(row, 2, item.manufacturer or "—", item)
            self._set_row_item(row, 3, str(item.priority), item)

            price = (
                f"${item.estimated_price_cents / 100:.2f}" if item.estimated_price_cents else "—"
            )
            self._set_row_item(row, 4, price, item)

            status_item = self._make_item(item, _status_text(item))
            if item.is_purchased:
                status_item.setForeground(QColor(PALETTE.text_secondary))
            self._table.setItem(row, 5, status_item)

        configure_table_columns(self._table, stretch_column=0)
        self._update_action_buttons()

    def _set_row_item(self, row: int, column: int, text: str, item: WishlistItemRead) -> None:
        self._table.setItem(row, column, self._make_item(item, text))

    def _make_item(self, item: WishlistItemRead, text: str) -> QTableWidgetItem:
        cell = QTableWidgetItem(text)
        cell.setData(Qt.ItemDataRole.UserRole, item)
        if item.is_deleted or item.is_purchased:
            cell.setForeground(QColor(PALETTE.text_disabled))
        return cell

    def _selected_item(self) -> WishlistItemRead | None:
        items = self._table.selectedItems()
        if not items:
            return None
        data = items[0].data(Qt.ItemDataRole.UserRole)
        assert isinstance(data, WishlistItemRead)
        return data

    def _update_action_buttons(self) -> None:
        item = self._selected_item()
        self._edit_button.setEnabled(item is not None)
        self._mark_purchased_button.setEnabled(
            item is not None and not item.is_deleted and not item.is_purchased
        )
        self._archive_button.setEnabled(item is not None and not item.is_deleted)
        self._restore_button.setEnabled(item is not None and item.is_deleted)

        self._inspector.set_details_widget(
            _build_wishlist_item_detail_widget(item) if item is not None else None
        )

    def _on_add(self) -> None:
        dialog = WishlistItemFormDialog(parent=self)
        accepted = dialog.exec() == WishlistItemFormDialog.DialogCode.Accepted
        data = dialog.result_data()
        if accepted and data is not None:
            self._service.create_item(data)
            self._notifications.post(
                "Item added to your wishlist.",
                severity=NotificationSeverity.SUCCESS,
                source="wishlist",
            )
            self._reload()

    def _on_edit(self) -> None:
        item = self._selected_item()
        if item is None:
            return
        dialog = WishlistItemFormDialog(existing=item, parent=self)
        accepted = dialog.exec() == WishlistItemFormDialog.DialogCode.Accepted
        data = dialog.result_data()
        if accepted and data is not None:
            try:
                self._service.update_item(item.id, data)
            except WishlistItemNotFoundError:
                QMessageBox.warning(self, "Item not found", "This wishlist item no longer exists.")
            else:
                self._notifications.post(
                    "Wishlist item updated.",
                    severity=NotificationSeverity.SUCCESS,
                    source="wishlist",
                )
            self._reload()

    def _on_mark_purchased(self) -> None:
        item = self._selected_item()
        if item is None:
            return

        if item.item_type != WishlistItemType.KIT.value:
            self._service.mark_purchased(item.id)
            self._notifications.post(
                f"'{item.name}' marked as purchased.",
                severity=NotificationSeverity.SUCCESS,
                source="wishlist",
            )
            self._reload()
            return

        reply = QMessageBox.question(
            self,
            "Create Kit Library entry?",
            f"Create a Kit Library entry for '{item.name}'? "
            "You'll be able to set its grade and other details next.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._service.mark_purchased(item.id)
        new_kit = self._kit_service.create_kit(
            KitCreate(
                name=item.name,
                manufacturer=item.manufacturer or "Unknown",
                grade=_DEFAULT_KIT_GRADE,
                status=CollectionStatus.OWNED_SEALED,
                purchase_price_cents=item.estimated_price_cents,
                purchase_date=date.today(),
            )
        )
        self._notifications.post(
            f"'{item.name}' marked as purchased and added to Kit Library.",
            severity=NotificationSeverity.SUCCESS,
            source="wishlist",
        )
        self._reload()

        kit_dialog = KitFormDialog(existing=new_kit, parent=self)
        if kit_dialog.exec() == KitFormDialog.DialogCode.Accepted:
            kit_data = kit_dialog.result_data()
            if kit_data is not None:
                self._kit_service.update_kit(new_kit.id, kit_data)

    def _on_archive(self) -> None:
        item = self._selected_item()
        if item is None:
            return
        if not confirm_destructive_action(
            self,
            title="Archive wishlist item",
            message=(
                f"Archive '{item.name}'? It will be hidden from the active list until restored."
            ),
            confirm_label="Archive",
        ):
            return
        self._service.archive_item(item.id)
        self._notifications.post(
            f"'{item.name}' archived.", severity=NotificationSeverity.INFO, source="wishlist"
        )
        self._reload()

    def _on_restore(self) -> None:
        item = self._selected_item()
        if item is None:
            return
        self._service.restore_item(item.id)
        self._notifications.post(
            f"'{item.name}' restored.", severity=NotificationSeverity.SUCCESS, source="wishlist"
        )
        self._reload()
