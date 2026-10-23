"""Task Repository and Checkpoint Engine for Project FRIDAY.

Provides structured persistence and crash recovery for tasks, subtasks, steps, and file modifications.
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.memory.database import db, Database


class TaskPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class TaskStep:
    id: Optional[int]
    task_id: int
    step_index: int
    description: str
    tool_name: Optional[str] = None
    tool_args: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    status: str = "PENDING"
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class Task:
    id: Optional[int]
    title: str
    description: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    project_id: Optional[int] = None
    due_date: Optional[str] = None
    estimated_minutes: int = 30
    progress_percent: int = 0
    error_message: Optional[str] = None
    steps: List[TaskStep] = field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TaskRepository:
    """Provides high-level repository access and checkpointing for tasks and steps."""

    def __init__(self, database: Optional[Database] = None):
        self.db = database or db

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: TaskPriority = TaskPriority.MEDIUM,
        project_id: Optional[int] = None,
        due_date: Optional[str] = None,
        estimated_minutes: int = 30,
    ) -> Task:
        """Create a new persistent task."""
        query = """
        INSERT INTO tasks (title, description, priority, status, project_id, due_date, estimated_minutes, progress_percent)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0);
        """
        task_id = self.db.execute_write(
            query,
            (title, description, priority.value, TaskStatus.PENDING.value, project_id, due_date, estimated_minutes),
        )
        return self.get_task(task_id)  # type: ignore

    def get_task(self, task_id: int) -> Optional[Task]:
        """Fetch a task and its associated steps."""
        rows = self.db.execute_query("SELECT * FROM tasks WHERE id = ?", (task_id,))
        if not rows:
            return None

        row = rows[0]
        step_rows = self.db.execute_query(
            "SELECT * FROM task_steps WHERE task_id = ? ORDER BY step_index ASC", (task_id,)
        )

        steps = [
            TaskStep(
                id=s["id"],
                task_id=s["task_id"],
                step_index=s["step_index"],
                description=s["description"],
                tool_name=s["tool_name"],
                tool_args=json.loads(s["tool_args_json"]) if s["tool_args_json"] else {},
                result=json.loads(s["result_json"]) if s["result_json"] else None,
                status=s["status"],
                created_at=s["created_at"],
                completed_at=s["completed_at"],
            )
            for s in step_rows
        ]

        return Task(
            id=row["id"],
            title=row["title"],
            description=row["description"] or "",
            priority=TaskPriority(row["priority"]),
            status=TaskStatus(row["status"]),
            project_id=row["project_id"],
            due_date=row["due_date"],
            estimated_minutes=row["estimated_minutes"],
            progress_percent=row["progress_percent"],
            error_message=row["error_message"],
            steps=steps,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def add_step(
        self,
        task_id: int,
        step_index: int,
        description: str,
        tool_name: Optional[str] = None,
        tool_args: Optional[Dict[str, Any]] = None,
    ) -> TaskStep:
        """Add a step checkpoint to an ongoing task."""
        query = """
        INSERT INTO task_steps (task_id, step_index, description, tool_name, tool_args_json, status)
        VALUES (?, ?, ?, ?, ?, 'PENDING');
        """
        step_id = self.db.execute_write(
            query,
            (
                task_id,
                step_index,
                description,
                tool_name,
                json.dumps(tool_args or {}),
            ),
        )
        return TaskStep(
            id=step_id,
            task_id=task_id,
            step_index=step_index,
            description=description,
            tool_name=tool_name,
            tool_args=tool_args or {},
            status="PENDING",
        )

    def update_step_result(
        self,
        task_id: int,
        step_index: int,
        status: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Checkpoint step completion and outcome."""
        query = """
        UPDATE task_steps
        SET status = ?, result_json = ?, completed_at = datetime('now')
        WHERE task_id = ? AND step_index = ?;
        """
        self.db.execute_write(
            query,
            (status, json.dumps(result or {}), task_id, step_index),
        )

    def update_task_status(
        self,
        task_id: int,
        status: TaskStatus,
        progress_percent: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update overall task state."""
        updates = ["status = ?", "updated_at = datetime('now')"]
        params: List[Any] = [status.value]

        if progress_percent is not None:
            updates.append("progress_percent = ?")
            params.append(progress_percent)

        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)

        params.append(task_id)
        query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?;"
        self.db.execute_write(query, tuple(params))

    def record_file_change(
        self,
        task_id: Optional[int],
        file_path: str,
        backup_path: Optional[str],
        change_type: str,
    ) -> None:
        """Record modified files for undo and recovery tracking."""
        query = """
        INSERT INTO file_changes (task_id, file_path, backup_path, change_type)
        VALUES (?, ?, ?, ?);
        """
        self.db.execute_write(query, (task_id, file_path, backup_path, change_type))

    def get_unfinished_tasks(self) -> List[Task]:
        """Return tasks that were in progress or waiting for approval before restart."""
        rows = self.db.execute_query(
            "SELECT id FROM tasks WHERE status IN ('IN_PROGRESS', 'WAITING_APPROVAL', 'PENDING') ORDER BY priority DESC, created_at ASC"
        )
        tasks = []
        for r in rows:
            t = self.get_task(r["id"])
            if t:
                tasks.append(t)
        return tasks

    def list_all_tasks(self, limit: int = 50) -> List[Task]:
        """List tasks ordered by update time."""
        rows = self.db.execute_query(
            "SELECT id FROM tasks ORDER BY updated_at DESC LIMIT ?", (limit,)
        )
        tasks = []
        for r in rows:
            t = self.get_task(r["id"])
            if t:
                tasks.append(t)
        return tasks

    def delete_task(self, task_id: int) -> bool:
        """Delete a task and cascade its steps."""
        self.db.execute_write("DELETE FROM tasks WHERE id = ?", (task_id,))
        return True


# Global repository singleton
task_repository = TaskRepository()
