"""A single, consistent confirmation prompt for destructive operations."""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget


def confirm_destructive_action(
    parent: QWidget | None,
    *,
    title: str,
    message: str,
    confirm_label: str = "Delete",
) -> bool:
    """Show a modal confirmation prompt and return whether the user confirmed."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(title)
    box.setText(message)
    confirm_button = box.addButton(confirm_label, QMessageBox.ButtonRole.DestructiveRole)
    box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(confirm_button)
    box.exec()
    return box.clickedButton() is confirm_button
