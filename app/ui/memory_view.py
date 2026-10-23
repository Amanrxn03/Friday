"""Memory Manager View for Project FRIDAY.

Provides inspection, editing, export, and deletion of persistent user facts, preferences,
and project roots. Strictly separates verified explicit statements from inferred habits.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QLineEdit, QComboBox, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt

from app.memory.memory_service import memory_service, MemoryItem
from app.ui.theme import COLOR_CYAN_ACCENT, COLOR_SUCCESS, COLOR_WARNING


class MemoryView(QWidget):
    """Declarative memory viewer and editor."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.refresh_table()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header Title
        title_box = QHBoxLayout()
        title_lbl = QLabel("LONG-TERM MEMORY & CONTEXT MANAGER")
        title_lbl.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {COLOR_CYAN_ACCENT};")
        title_box.addWidget(title_lbl)
        title_box.addStretch()

        self.btn_export = QPushButton("💾 Export JSON")
        self.btn_export.setProperty("class", "secondary-btn")
        self.btn_export.clicked.connect(self._export_memory)
        title_box.addWidget(self.btn_export)

        self.btn_clear = QPushButton("🗑️ Clear All")
        self.btn_clear.setProperty("class", "danger-btn")
        self.btn_clear.clicked.connect(self._clear_all_memory)
        title_box.addWidget(self.btn_clear)

        layout.addLayout(title_box)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Key", "Value", "Category", "Verification Status", "Last Updated"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        # Add Memory Form
        form_box = QHBoxLayout()
        self.txt_key = QLineEdit()
        self.txt_key.setPlaceholderText("Key (e.g., preferred_editor)")
        form_box.addWidget(self.txt_key)

        self.txt_val = QLineEdit()
        self.txt_val.setPlaceholderText("Value (e.g., VS Code)")
        form_box.addWidget(self.txt_val)

        self.combo_cat = QComboBox()
        self.combo_cat.addItems(["preference", "project", "system", "general"])
        form_box.addWidget(self.combo_cat)

        self.btn_add = QPushButton("+ Add Fact")
        self.btn_add.setProperty("class", "primary-btn")
        self.btn_add.clicked.connect(self._add_memory_item)
        form_box.addWidget(self.btn_add)

        self.btn_delete = QPushButton("Delete Selected")
        self.btn_delete.setProperty("class", "secondary-btn")
        self.btn_delete.clicked.connect(self._delete_selected)
        form_box.addWidget(self.btn_delete)

        layout.addLayout(form_box)

    def refresh_table(self) -> None:
        """Fetch and render stored memory rows."""
        items = memory_service.list_items()
        self.table.setRowCount(len(items))

        for row, item in enumerate(items):
            self.table.setItem(row, 0, QTableWidgetItem(item.key))
            self.table.setItem(row, 1, QTableWidgetItem(item.value))
            self.table.setItem(row, 2, QTableWidgetItem(item.category))

            status_str = "Verified Fact" if item.is_verified else "Inferred Preference"
            item_status = QTableWidgetItem(status_str)
            item_status.setForeground(Qt.green if item.is_verified else Qt.yellow)
            self.table.setItem(row, 3, item_status)

            self.table.setItem(row, 4, QTableWidgetItem(item.updated_at[:16]))

    def _add_memory_item(self) -> None:
        key = self.txt_key.text().strip()
        val = self.txt_val.text().strip()
        cat = self.combo_cat.currentText()
        if not key or not val:
            return

        memory_service.remember(key, val, category=cat, is_verified=True)
        self.txt_key.clear()
        self.txt_val.clear()
        self.refresh_table()

    def _delete_selected(self) -> None:
        selected = self.table.currentRow()
        if selected >= 0:
            key_item = self.table.item(selected, 0)
            if key_item:
                memory_service.forget(key_item.text())
                self.refresh_table()

    def _export_memory(self) -> None:
        json_data = memory_service.export_memory_json()
        path, _ = QFileDialog.getSaveFileName(self, "Export Memory", "friday_memory.json", "JSON Files (*.json)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(json_data)
                QMessageBox.information(self, "Exported", f"Successfully exported memory to {path}")
            except Exception as e:
                QMessageBox.warning(self, "Export Failed", str(e))

    def _clear_all_memory(self) -> None:
        confirm = QMessageBox.question(
            self, "Confirm Reset", "Are you sure you want to delete all stored long-term memory?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            memory_service.clear_all()
            self.refresh_table()
