"""Path Policy and Traversal Protection for Project FRIDAY.

Validates that all file, folder, and automation operations are restricted to allowed
working directories and never tamper with sensitive OS or system directories.
"""

from pathlib import Path
from typing import List, Optional, Union
import os
import re

from app.config import config


class PathPolicyError(PermissionError):
    """Raised when an operation attempts to access an unauthorized or dangerous path."""
    pass


class PathPolicy:
    """Enforces strict path containment, traversal protection, and allowlists."""

    # Disallowed system and device file names on Windows
    WINDOWS_RESERVED_NAMES = {
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
    }

    def __init__(self, allowed_roots: Optional[List[Path]] = None):
        self.allowed_roots: List[Path] = [
            r.resolve() for r in (allowed_roots or config.paths.allowed_roots)
        ]

    def add_allowed_root(self, root: Union[str, Path]) -> None:
        """Add an authorized project or workspace directory."""
        resolved = Path(root).resolve()
        if resolved not in self.allowed_roots:
            self.allowed_roots.append(resolved)

    def validate_path(self, target: Union[str, Path], write: bool = False) -> Path:
        """Validate that a target path is strictly contained within an authorized root.

        Args:
            target: The file or folder path to check.
            write: If True, enforces strict write permissions (no system directories, no root drive, no dotfiles).

        Returns:
            The fully resolved, canonicalized Path object.

        Raises:
            PathPolicyError: If the path is outside allowed roots or violates safety policies.
        """
        if not target or str(target).strip() == "":
            raise PathPolicyError("Empty path is invalid")

        raw_str = str(target).strip()

        # Check for alternate data streams (e.g., file.txt:hidden)
        if ":" in raw_str[2:]:  # allow Windows drive letter at index 1
            raise PathPolicyError(f"Alternate data streams are strictly prohibited: {raw_str}")

        # Guard against Windows reserved device names
        stem = Path(raw_str).stem.upper()
        if stem in self.WINDOWS_RESERVED_NAMES:
            raise PathPolicyError(f"Access to Windows reserved device name '{stem}' is blocked")

        try:
            resolved = Path(raw_str).resolve()
        except Exception as e:
            raise PathPolicyError(f"Could not resolve path '{raw_str}': {e}")

        # Check denied patterns
        path_str = str(resolved).lower()
        for denied in config.paths.denied_patterns:
            if denied.lower() in path_str:
                raise PathPolicyError(f"Access to protected system pattern '{denied}' is blocked: {resolved}")

        # Check containment in allowed roots
        is_contained = False
        for root in self.allowed_roots:
            try:
                resolved.relative_to(root)
                is_contained = True
                break
            except ValueError:
                continue

        if not is_contained:
            # Check if it matches user's home documents or workspace
            raise PathPolicyError(
                f"Path '{resolved}' is outside authorized working roots: "
                f"{[str(r) for r in self.allowed_roots]}"
            )

        # Extra checks for write operations
        if write:
            if resolved.name.startswith(".env") or resolved.name == ".git":
                raise PathPolicyError(f"Modifying critical sensitive file '{resolved.name}' is prohibited")

        return resolved

    def is_safe(self, target: Union[str, Path], write: bool = False) -> bool:
        """Helper to test path safety without raising an exception."""
        try:
            self.validate_path(target, write=write)
            return True
        except PathPolicyError:
            return False


# Global singleton
path_policy = PathPolicy()
