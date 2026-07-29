"""The "start a new build" dialog: pick a kit, a template, and a title."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from gunpla_fabrication_suite.plugins.build_planner.schemas import BuildProjectCreate
from gunpla_fabrication_suite.plugins.build_planner.templates import BUILTIN_TEMPLATES
from gunpla_fabrication_suite.plugins.kit_library.schemas import KitRead
from gunpla_fabrication_suite.plugins.kit_library.services.kit_service import KitService
from gunpla_fabrication_suite.themes import PALETTE


class NewBuildDialog(QDialog):
    """A modal form for starting a new build from an existing kit."""

    def __init__(self, kit_service: KitService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Start a New Build")
        self.setMinimumWidth(420)

        self._kits = kit_service.list_kits()

        outer = QVBoxLayout(self)

        self._error_label = QLabel()
        self._error_label.setStyleSheet(f"color: {PALETTE.danger};")
        self._error_label.hide()
        outer.addWidget(self._error_label)

        form = QFormLayout()
        outer.addLayout(form)

        self._kit_combo = QComboBox()
        if self._kits:
            for kit in self._kits:
                self._kit_combo.addItem(f"{kit.manufacturer} — {kit.name} ({kit.grade})", kit)
            self._kit_combo.currentIndexChanged.connect(self._on_kit_changed)
        else:
            self._kit_combo.addItem("No kits in your library yet", None)
            self._kit_combo.setEnabled(False)
        form.addRow("Kit*", self._kit_combo)

        self._template_combo = QComboBox()
        for template in BUILTIN_TEMPLATES:
            self._template_combo.addItem(template.label, template.key)
        form.addRow("Template*", self._template_combo)

        self._title_edit = QLineEdit()
        form.addRow("Build title*", self._title_edit)

        self._commission_checkbox = QCheckBox("This is a commission build")
        form.addRow("", self._commission_checkbox)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

        self._result_data: BuildProjectCreate | None = None
        if self._kits:
            self._on_kit_changed(0)

    def _on_kit_changed(self, index: int) -> None:
        kit: KitRead | None = self._kit_combo.itemData(index)
        if kit is not None and not self._title_edit.text().strip():
            self._title_edit.setText(f"{kit.name}")

    def _on_accept(self) -> None:
        kit: KitRead | None = self._kit_combo.currentData()
        title = self._title_edit.text().strip()

        if kit is None or not title:
            self._error_label.setText("Choose a kit and enter a build title.")
            self._error_label.show()
            return

        self._result_data = BuildProjectCreate(
            kit_id=kit.id,
            title=title,
            template_key=self._template_combo.currentData(),
            is_commission=self._commission_checkbox.isChecked(),
        )
        self.accept()

    def result_data(self) -> BuildProjectCreate | None:
        """The validated form data, populated only after a successful accept."""
        return self._result_data
