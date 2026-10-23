"""SQLite Database Manager for Project FRIDAY.

Provides connection pooling, WAL journaling mode, relational schemas for tasks, steps,
preferences, facts, projects, briefings, and auditable events.
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager

from app.config import config

logger = logging.getLogger(__name__)


class Database:
    """Manages the SQLite database with WAL mode and robust crash resilience."""

    SCHEMA = """
    PRAGMA foreign_keys = ON;
    PRAGMA journal_mode = WAL;

    -- Facts and Preferences (Distinguishes verified explicit facts vs inferred preferences)
    CREATE TABLE IF NOT EXISTS memory_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE NOT NULL,
        value TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'general',
        is_verified INTEGER NOT NULL DEFAULT 1,  -- 1 = explicit user statement, 0 = inferred
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- Active and Past Projects
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        root_path TEXT NOT NULL,
        description TEXT,
        status TEXT NOT NULL DEFAULT 'ACTIVE',  -- ACTIVE, ARCHIVED, COMPLETED
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- Tasks and Workflows
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        priority TEXT NOT NULL DEFAULT 'MEDIUM',  -- LOW, MEDIUM, HIGH, URGENT
        status TEXT NOT NULL DEFAULT 'PENDING',    -- PENDING, IN_PROGRESS, WAITING_APPROVAL, COMPLETED, FAILED, CANCELLED
        project_id INTEGER,
        due_date TEXT,
        estimated_minutes INTEGER DEFAULT 30,
        progress_percent INTEGER DEFAULT 0,
        error_message TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
    );

    -- Granular Steps for Task Checkpointing and Resumability
    CREATE TABLE IF NOT EXISTS task_steps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL,
        step_index INTEGER NOT NULL,
        description TEXT NOT NULL,
        tool_name TEXT,
        tool_args_json TEXT,
        result_json TEXT,
        status TEXT NOT NULL DEFAULT 'PENDING',  -- PENDING, IN_PROGRESS, COMPLETED, FAILED, SKIPPED
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        completed_at TEXT,
        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
        UNIQUE (task_id, step_index)
    );

    -- File Modifications for Recovery and Undo
    CREATE TABLE IF NOT EXISTS file_changes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER,
        file_path TEXT NOT NULL,
        backup_path TEXT,
        change_type TEXT NOT NULL,  -- CREATED, MODIFIED, DELETED
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
    );

    -- Morning Briefings
    CREATE TABLE IF NOT EXISTS daily_briefings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date_str TEXT UNIQUE NOT NULL,
        news_json TEXT NOT NULL,
        weather_summary TEXT,
        task_summary TEXT,
        spoken_audio_path TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- Security Audit Trail
    CREATE TABLE IF NOT EXISTS audit_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        action TEXT NOT NULL,
        status TEXT NOT NULL,
        confirmed_by_user INTEGER NOT NULL DEFAULT 0,
        details_json TEXT,
        timestamp TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- Indexes for Rapid Querying
    CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
    CREATE INDEX IF NOT EXISTS idx_task_steps_task ON task_steps(task_id);
    CREATE INDEX IF NOT EXISTS idx_memory_category ON memory_items(category);
    CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp);
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.database_path
        self._ensure_parent_dir()
        self.initialize_schema()

    def _ensure_parent_dir(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        """Create a connection with foreign keys and row factory enabled."""
        conn = sqlite3.connect(str(self.db_path), timeout=20.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    @contextmanager
    def transaction(self):
        """Context manager for atomic database transactions."""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error("Database transaction rolled back due to error: %s", e)
            raise
        finally:
            conn.close()

    def initialize_schema(self) -> None:
        """Create database tables and indexes if they do not exist."""
        with self.transaction() as conn:
            conn.executescript(self.SCHEMA)
        logger.info("FRIDAY Database initialized successfully at %s", self.db_path)

    def execute_query(self, query: str, params: Tuple = ()) -> List[sqlite3.Row]:
        """Execute a read query and return rows."""
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(query, params)
            return cur.fetchall()
        finally:
            conn.close()

    def execute_write(self, query: str, params: Tuple = ()) -> int:
        """Execute an insert/update query and return the last row ID."""
        with self.transaction() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            return cur.lastrowid or 0


# Global database singleton
db = Database()
