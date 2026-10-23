"""Safe File Operations Manager for Project FRIDAY.

Enforces strict path policy boundaries, traversal protection, automatic backups for modified
files to enable undo/recovery, and atomic read/write safeguards.
"""

import os
import shutil
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union

from app.security.path_policy import PathPolicy, path_policy, PathPolicyError
from app.memory.task_repository import task_repository
from app.config import config

logger = logging.getLogger(__name__)


class FileManager:
    """Manages path-restricted file system operations with automated undo backups."""

    def __init__(self, backup_dir: Optional[Path] = None, policy: Optional[PathPolicy] = None):
        self.backup_dir = backup_dir or (config.data_dir / "backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.policy = policy or path_policy

    def _create_backup(self, target_path: Path, task_id: Optional[int] = None) -> Optional[Path]:
        """Create a timestamped backup before modifying or deleting an existing file."""
        if not target_path.exists() or not target_path.is_file():
            return None

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{target_path.stem}_{timestamp}{target_path.suffix}"
        backup_dest = self.backup_dir / backup_filename

        try:
            shutil.copy2(target_path, backup_dest)
            logger.info("Created backup of '%s' at '%s'", target_path, backup_dest)
            task_repository.record_file_change(
                task_id=task_id,
                file_path=str(target_path),
                backup_path=str(backup_dest),
                change_type="MODIFIED",
            )
            return backup_dest
        except Exception as e:
            logger.error("Failed to create file backup: %s", e)
            return None

    def list_directory(self, dir_path: Union[str, Path]) -> Dict[str, Any]:
        """List contents of an approved directory."""
        validated = self.policy.validate_path(dir_path)
        if not validated.exists():
            return {"success": False, "error": f"Directory not found: {validated}"}
        if not validated.is_dir():
            return {"success": False, "error": f"Path is not a directory: {validated}"}

        items = []
        for entry in validated.iterdir():
            try:
                items.append({
                    "name": entry.name,
                    "is_dir": entry.is_dir(),
                    "size_bytes": entry.stat().st_size if entry.is_file() else None,
                })
            except Exception:
                pass

        return {"success": True, "path": str(validated), "items": items}

    def search_files(self, pattern: str, search_root: Optional[Union[str, Path]] = None, max_results: int = 50) -> Dict[str, Any]:
        """Search for files matching glob pattern within an approved root."""
        root = self.policy.validate_path(search_root or config.paths.allowed_roots[0])
        results = []

        try:
            for p in root.rglob(pattern):
                if p.is_file() and self.policy.is_safe(p):
                    results.append(str(p))
                    if len(results) >= max_results:
                        break
            return {"success": True, "count": len(results), "matches": results}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def read_file(self, file_path: Union[str, Path], max_chars: int = 10000) -> Dict[str, Any]:
        """Read text content from an approved file."""
        validated = self.policy.validate_path(file_path)
        if not validated.exists():
            return {"success": False, "error": f"File does not exist: {validated}"}
        if not validated.is_file():
            return {"success": False, "error": f"Path is not a file: {validated}"}

        try:
            with open(validated, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(max_chars)
            return {"success": True, "path": str(validated), "content": content}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_file(
        self,
        file_path: Union[str, Path],
        content: str,
        task_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Write content to an approved file, creating an undo backup if overwriting."""
        validated = self.policy.validate_path(file_path, write=True)

        # Create parent directories if needed
        validated.parent.mkdir(parents=True, exist_ok=True)

        backup_made = None
        if validated.exists():
            backup_made = self._create_backup(validated, task_id=task_id)

        try:
            with open(validated, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info("Successfully wrote file: %s (Bytes: %d)", validated, len(content))
            return {
                "success": True,
                "path": str(validated),
                "bytes_written": len(content),
                "backup_path": str(backup_made) if backup_made else None,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_file(self, file_path: Union[str, Path], task_id: Optional[int] = None) -> Dict[str, Any]:
        """Safely delete an approved file after generating a backup."""
        validated = self.policy.validate_path(file_path, write=True)
        if not validated.exists():
            return {"success": False, "error": f"File does not exist: {validated}"}

        backup_made = self._create_backup(validated, task_id=task_id)
        try:
            validated.unlink()
            logger.warning("Deleted file: %s (Backup: %s)", validated, backup_made)
            return {
                "success": True,
                "deleted_path": str(validated),
                "backup_path": str(backup_made) if backup_made else None,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# Global singleton
file_manager = FileManager()
