"""The Supplies page: a filterable table with add/edit/archive actions."""

from __future__ import annotations

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
from gunpla_fabrication_suite.plugins.supplies.models.supply import SupplyCategory
from gunpla_fabrication_suite.plugins.supplies.schemas import SupplyRead
from gunpla_fabrication_suite.plugins.supplies.services.supply_service import (
    SupplyNotFoundError,
    SupplyService,
)
from gunpla_fabrication_suite.plugins.supplies.ui.supply_dialog import SupplyFormDialog
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

_COLUMNS = ("Name", "Brand", "Category", "Color", "Quantity", "Unit", "Status", "Price")

_ALL_CATEGORIES = "All categories"


def _build_supply_detail_widget(supply: SupplyRead) -> QWidget:
    """A standalone widget summarizing ``supply``, for the shared Inspector panel."""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)

    name_label = QLabel(supply.name)
    set_label_role(name_label, "section-title")
    layout.addWidget(name_label)

    subtitle_label = QLabel(f"{supply.brand} — {supply.category.title()}")
    set_label_role(subtitle_label, "secondary")
    layout.addWidget(subtitle_label)

    layout.addSpacing(8)
    price = f"${supply.purchase_price_cents / 100:.2f}" if supply.purchase_price_cents else "—"
    status = "Low Stock" if supply.is_low_stock else "OK"
    for title, value in (
        ("Color", supply.color_name or "—"),
        ("Quantity", f"{supply.quantity_on_hand:g} {supply.unit}"),
        ("Status", status),
        ("Price", price),
        ("Tags", ", ".join(supply.tags) or "None"),
        ("Notes", supply.notes or "None"),
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


class SuppliesPage(QWidget):
    """Lists supplies and lets the user add, edit, archive, and restore them."""

    def __init__(
        self,
        service: SupplyService,
        notifications: NotificationCenter,
        inspector: InspectorPanel,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._notifications = notifications
        self._inspector = inspector
        self._supplies: list[SupplyRead] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)

        add_button = QPushButton("Add Supply")
        set_button_kind(add_button, "primary")
        add_button.clicked.connect(self._on_add)
        outer.addWidget(PageHeader("Supplies", actions=[add_button]))

        toolbar_row = QHBoxLayout()
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Filter by brand or name…")
        self._search_edit.textChanged.connect(self._refresh_table)
        toolbar_row.addWidget(self._search_edit, stretch=1)

        self._category_combo = QComboBox()
        self._category_combo.addItem(_ALL_CATEGORIES, None)
        for category in SupplyCategory:
            self._category_combo.addItem(category.value.title(), category)
        self._category_combo.currentIndexChanged.connect(self._refresh_table)
        toolbar_row.addWidget(self._category_combo)

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

        self._empty_state = EmptyStateWidget(
            title="No supplies yet",
            description="Add your paints, cement, tools, and other hobby supplies to track them.",
            action_label="Add Supply",
            on_action=self._on_add,
        )
        self._stack.addWidget(self._empty_state)

        card = Card()
        card.add_widget(stack_container, stretch=1)
        outer.addWidget(card, 1)

        self._reload()

    def _reload(self) -> None:
        self._supplies = self._service.list_supplies(
            include_archived=self._show_archived_checkbox.isChecked()
        )
        self._refresh_table()

    def show_supply(self, supply_id: str) -> None:
        """Select ``supply_id`` in the table, the same as a user clicking its row."""
        self._search_edit.clear()
        self._category_combo.setCurrentIndex(0)
        target = next(
            (s for s in self._service.list_supplies(include_archived=True) if s.id == supply_id),
            None,
        )
        if target is not None and target.is_deleted:
            self._show_archived_checkbox.setChecked(True)
        self._reload()
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item is None:
                continue
            data = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(data, SupplyRead) and data.id == supply_id:
                self._table.selectRow(row)
                self._table.scrollToItem(item)
                return

    def _visible_supplies(self) -> list[SupplyRead]:
        query = self._search_edit.text().strip().lower()
        # currentData() round-trips SupplyCategory (a StrEnum, itself a str
        # subclass) through QVariant as a plain str, not the enum member —
        # compare the string value directly rather than via `.value`.
        category = self._category_combo.currentData()
        return [
            supply
            for supply in self._supplies
            if (not query or query in supply.name.lower() or query in supply.brand.lower())
            and (category is None or supply.category == category)
        ]

    def _refresh_table(self) -> None:
        if not self._supplies:
            self._table.setRowCount(0)
            self._stack.setCurrentWidget(self._empty_state)
            return
        self._stack.setCurrentWidget(self._table)

        visible = self._visible_supplies()
        self._table.setRowCount(len(visible))
        for row, supply in enumerate(visible):
            self._set_row_item(row, 0, supply.name, supply)
            self._set_row_item(row, 1, supply.brand, supply)
            self._set_row_item(row, 2, supply.category.title(), supply)

            color_item = self._make_item(supply, supply.color_name or "—")
            if supply.color_hex:
                color_item.setBackground(QColor(supply.color_hex))
            self._table.setItem(row, 3, color_item)

            self._set_row_item(row, 4, f"{supply.quantity_on_hand:g}", supply)
            self._set_row_item(row, 5, supply.unit, supply)

            status_item = self._make_item(
                supply, "Low Stock" if supply.is_low_stock else "OK"
            )
            if supply.is_low_stock:
                status_item.setForeground(QColor(PALETTE.warning))
            self._table.setItem(row, 6, status_item)

            price = (
                f"${supply.purchase_price_cents / 100:.2f}"
                if supply.purchase_price_cents
                else "—"
            )
            self._set_row_item(row, 7, price, supply)

        configure_table_columns(self._table, stretch_column=0)
        self._update_action_buttons()

    def _set_row_item(self, row: int, column: int, text: str, supply: SupplyRead) -> None:
        self._table.setItem(row, column, self._make_item(supply, text))

    def _make_item(self, supply: SupplyRead, text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, supply)
        if supply.is_deleted:
            item.setForeground(QColor(PALETTE.text_disabled))
        return item

    def _selected_supply(self) -> SupplyRead | None:
        items = self._table.selectedItems()
        if not items:
            return None
        data = items[0].data(Qt.ItemDataRole.UserRole)
        assert isinstance(data, SupplyRead)
        return data

    def _update_action_buttons(self) -> None:
        supply = self._selected_supply()
        self._edit_button.setEnabled(supply is not None)
        self._archive_button.setEnabled(supply is not None and not supply.is_deleted)
        self._restore_button.setEnabled(supply is not None and supply.is_deleted)

        # The shared Inspector panel is relevant regardless of which layout
        # is active — Rail and Command Deck just collapse it to 0 width by
        # default, but a user can still drag it open manually.
        self._inspector.set_details_widget(
            _build_supply_detail_widget(supply) if supply is not None else None
        )

    def _on_add(self) -> None:
        dialog = SupplyFormDialog(parent=self)
        accepted = dialog.exec() == SupplyFormDialog.DialogCode.Accepted
        data = dialog.result_data()
        if accepted and data is not None:
            self._service.create_supply(data)
            self._notifications.post(
                "Supply added to your inventory.",
                severity=NotificationSeverity.SUCCESS,
                source="supplies",
            )
            self._reload()

    def _on_edit(self) -> None:
        supply = self._selected_supply()
        if supply is None:
            return
        dialog = SupplyFormDialog(existing=supply, parent=self)
        accepted = dialog.exec() == SupplyFormDialog.DialogCode.Accepted
        data = dialog.result_data()
        if accepted and data is not None:
            try:
                self._service.update_supply(supply.id, data)
            except SupplyNotFoundError:
                QMessageBox.warning(self, "Supply not found", "This supply no longer exists.")
            else:
                self._notifications.post(
                    "Supply updated.", severity=NotificationSeverity.SUCCESS, source="supplies"
                )
            self._reload()

    def _on_archive(self) -> None:
        supply = self._selected_supply()
        if supply is None:
            return
        if not confirm_destructive_action(
            self,
            title="Archive supply",
            message=(
                f"Archive '{supply.name}'? It will be hidden from the active list until restored."
            ),
            confirm_label="Archive",
        ):
            return
        self._service.archive_supply(supply.id)
        self._notifications.post(
            f"'{supply.name}' archived.", severity=NotificationSeverity.INFO, source="supplies"
        )
        self._reload()

    def _on_restore(self) -> None:
        supply = self._selected_supply()
        if supply is None:
            return
        self._service.restore_supply(supply.id)
        self._notifications.post(
            f"'{supply.name}' restored.", severity=NotificationSeverity.SUCCESS, source="supplies"
        )
        self._reload()
