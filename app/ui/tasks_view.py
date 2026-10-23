"""Tasks and Workflow Continuity View for Project FRIDAY.

Manages persistent task queues, step checkpoints, priority rankings, and resumable execution states.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QLineEdit, QComboBox, QProgressBar, QMessageBox
)
from PySide6.QtCore import Qt

from app.memory.task_repository import task_repository, TaskPriority, TaskStatus, Task
from app.ui.theme import COLOR_CYAN_ACCENT, COLOR_WARNING, COLOR_SUCCESS


class TasksView(QWidget):
    """Task continuity and workflow progress panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.refresh_tasks()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Header Title
        title_box = QHBoxLayout()
        title_lbl = QLabel("TASKS, CHECKPOINTS & WORKFLOW CONTINUITY")
        title_lbl.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {COLOR_CYAN_ACCENT};")
        title_box.addWidget(title_lbl)
        title_box.addStretch()

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.setProperty("class", "secondary-btn")
        self.btn_refresh.clicked.connect(self.refresh_tasks)
        title_box.addWidget(self.btn_refresh)

        layout.addLayout(title_box)

        # Task Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Title", "Priority", "Status", "Progress", "Steps Checkpointed"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        # Quick Add Row
        add_box = QHBoxLayout()
        self.txt_title = QLineEdit()
        self.txt_title.setPlaceholderText("New task title (e.g., Audit project security policies)")
        add_box.addWidget(self.txt_title)

        self.combo_priority = QComboBox()
        self.combo_priority.addItems(["LOW", "MEDIUM", "HIGH", "URGENT"])
        self.combo_priority.setCurrentText("MEDIUM")
        add_box.addWidget(self.combo_priority)

        self.btn_add_task = QPushButton("+ Create Task")
        self.btn_add_task.setProperty("class", "primary-btn")
        self.btn_add_task.clicked.connect(self._create_task)
        add_box.addWidget(self.btn_add_task)

        self.btn_delete_task = QPushButton("Delete Task")
        self.btn_delete_task.setProperty("class", "secondary-btn")
        self.btn_delete_task.clicked.connect(self._delete_task)
        add_box.addWidget(self.btn_delete_task)

        layout.addLayout(add_box)

    def refresh_tasks(self) -> None:
        """Fetch and render all persistent tasks."""
        tasks = task_repository.list_all_tasks(limit=100)
        self.table.setRowCount(len(tasks))

        for row, t in enumerate(tasks):
            self.table.setItem(row, 0, QTableWidgetItem(str(t.id)))
            self.table.setItem(row, 1, QTableWidgetItem(t.title))

            # Priority
            p_item = QTableWidgetItem(t.priority.value)
            self.table.setItem(row, 2, p_item)

            # Status
            s_item = QTableWidgetItem(t.status.value)
            if t.status == TaskStatus.COMPLETED:
                s_item.setForeground(Qt.green)
            elif t.status == TaskStatus.WAITING_APPROVAL:
                s_item.setForeground(Qt.yellow)
            self.table.setItem(row, 3, s_item)

            # Progress
            self.table.setItem(row, 4, QTableWidgetItem(f"{t.progress_percent}%"))

            # Steps
            self.table.setItem(row, 5, QTableWidgetItem(f"{len(t.steps)} step(s)"))

    def _create_task(self) -> None:
        title = self.txt_title.text().strip()
        if not title:
            return

        priority = TaskPriority(self.combo_priority.currentText())
        task_repository.create_task(title=title, priority=priority)
        self.txt_title.clear()
        self.refresh_tasks()

    def _delete_task(self) -> None:
        selected = self.table.currentRow()
        if selected >= 0:
            id_item = self.table.item(selected, 0)
            if id_item:
                task_repository.delete_task(int(id_item.text()))
                self.refresh_tasks()
