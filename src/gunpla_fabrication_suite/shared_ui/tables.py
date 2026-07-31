"""Consistent column sizing for QTableWidget-based pages."""

from __future__ import annotations

from PySide6.QtWidgets import QHeaderView, QTableWidget


def configure_table_columns(
    table: QTableWidget,
    *,
    stretch_column: int | None = None,
    tooltip_columns: tuple[int, ...] = (),
) -> None:
    """Auto-fit every column to its current content, then optionally stretch one.

    Call this *after* populating the table's rows, on every refresh — not
    once at construction — since ``resizeColumnsToContents()`` only measures
    rows that exist right now; calling it against an empty table is a no-op
    and columns never get re-measured as data changes later.

    ``tooltip_columns`` sets each cell's tooltip to its own full text, for
    columns whose values may still be wider than the space available. Qt's
    default item elide already shows "…" when a column is too narrow, but a
    tooltip makes the full value readable without needing to widen the
    column (useful for something like a joined "Dependencies" list that
    would otherwise force a much wider table just to avoid ever truncating).
    """
    table.resizeColumnsToContents()

    if stretch_column is not None:
        header = table.horizontalHeader()
        for column in range(table.columnCount()):
            if column == stretch_column:
                header.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)
            elif header.sectionResizeMode(column) == QHeaderView.ResizeMode.Stretch:
                # Only one column may actually stretch at a time — a second
                # Stretch column fights the first for leftover space and
                # collapses to a near-zero width.
                header.setSectionResizeMode(column, QHeaderView.ResizeMode.Interactive)

    for column in tooltip_columns:
        for row in range(table.rowCount()):
            item = table.item(row, column)
            if item is not None:
                item.setToolTip(item.text())
