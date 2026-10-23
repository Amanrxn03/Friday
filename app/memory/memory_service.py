"""Long-Term Memory Service for Project FRIDAY.

Manages persistent user facts, preferences, project roots, and contextual decisions.
Strictly distinguishes explicit user statements from inferred preferences.
Supports privacy mode and memory exports.
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.memory.database import db, Database

logger = logging.getLogger(__name__)


@dataclass
class MemoryItem:
    id: int
    key: str
    value: str
    category: str
    is_verified: bool
    created_at: str
    updated_at: str


class MemoryService:
    """Manages long-term declarative memory and preferences."""

    def __init__(self, database: Optional[Database] = None):
        self.db = database or db
        self.privacy_mode_enabled = False

    def set_privacy_mode(self, enabled: bool) -> None:
        """Toggle privacy mode. When active, no new memory is written to disk."""
        self.privacy_mode_enabled = enabled
        logger.info("FRIDAY Memory Privacy Mode set to: %s", enabled)

    def remember(
        self,
        key: str,
        value: str,
        category: str = "general",
        is_verified: bool = True,
    ) -> bool:
        """Store or update a memory item.

        Args:
            key: Semantic identifier (e.g., 'preferred_code_editor', 'user_timezone').
            value: The stored data string or JSON.
            category: 'preference', 'project', 'system', 'contact', etc.
            is_verified: True if explicitly stated by the user; False if inferred.
        """
        if self.privacy_mode_enabled:
            logger.info("Privacy mode active: skipping memory persistence for key: %s", key)
            return False

        key_clean = key.strip()
        value_clean = value.strip()
        category_clean = category.strip().lower()

        query = """
        INSERT INTO memory_items (key, value, category, is_verified, updated_at)
        VALUES (?, ?, ?, ?, datetime('now'))
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            category = excluded.category,
            is_verified = excluded.is_verified,
            updated_at = datetime('now');
        """
        self.db.execute_write(
            query,
            (key_clean, value_clean, category_clean, 1 if is_verified else 0),
        )
        return True

    def recall(self, key: str) -> Optional[str]:
        """Retrieve a specific memory item by key."""
        rows = self.db.execute_query(
            "SELECT value FROM memory_items WHERE key = ?", (key.strip(),)
        )
        if rows:
            return rows[0]["value"]
        return None

    def list_items(self, category: Optional[str] = None) -> List[MemoryItem]:
        """List stored items, optionally filtered by category."""
        if category:
            rows = self.db.execute_query(
                "SELECT * FROM memory_items WHERE category = ? ORDER BY key ASC",
                (category.strip().lower(),),
            )
        else:
            rows = self.db.execute_query(
                "SELECT * FROM memory_items ORDER BY category ASC, key ASC"
            )

        return [
            MemoryItem(
                id=r["id"],
                key=r["key"],
                value=r["value"],
                category=r["category"],
                is_verified=bool(r["is_verified"]),
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    def forget(self, key: str) -> bool:
        """Delete a specific memory item."""
        self.db.execute_write("DELETE FROM memory_items WHERE key = ?", (key.strip(),))
        return True

    def clear_all(self) -> None:
        """Wipe all stored declarative memory (user data privacy request)."""
        self.db.execute_write("DELETE FROM memory_items;")
        logger.warning("All long-term declarative memory cleared by user request.")

    def export_memory_json(self) -> str:
        """Export all stored items as a readable JSON string."""
        items = self.list_items()
        data = [
            {
                "key": item.key,
                "value": item.value,
                "category": item.category,
                "is_verified": item.is_verified,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
            for item in items
        ]
        return json.dumps(data, indent=2)

    def register_project(self, name: str, root_path: str, description: str = "") -> int:
        """Register or update an active project root path."""
        query = """
        INSERT INTO projects (name, root_path, description, status, updated_at)
        VALUES (?, ?, ?, 'ACTIVE', datetime('now'))
        ON CONFLICT(name) DO UPDATE SET
            root_path = excluded.root_path,
            description = excluded.description,
            status = 'ACTIVE',
            updated_at = datetime('now');
        """
        return self.db.execute_write(query, (name.strip(), root_path.strip(), description.strip()))

    def list_active_projects(self) -> List[Dict[str, Any]]:
        """List all active tracked projects."""
        rows = self.db.execute_query("SELECT * FROM projects WHERE status = 'ACTIVE' ORDER BY name ASC")
        return [dict(r) for r in rows]


# Global memory service singleton
memory_service = MemoryService()
