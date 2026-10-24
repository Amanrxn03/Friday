"""Unit tests for Phase 4: Desktop Controls, Safe File Operations, Tool Registry, and Execution Manager."""

import tempfile
from pathlib import Path
import pytest

from app.core.tool_registry import ToolRegistry, register_default_tools
from app.core.execution_manager import ExecutionManager
from app.core.permissions import PermissionsEngine
from app.config import AutonomyMode
from app.security.path_policy import PathPolicy
from app.desktop.file_manager import FileManager


def test_tool_registry_and_schemas():
    """Ensure tool registry registers default tools and creates valid OpenAI schemas."""
    registry = ToolRegistry()
    register_default_tools(registry)

    schemas = registry.get_openai_tool_schemas()
    assert len(schemas) >= 12

    tool_names = [s["function"]["name"] for s in schemas]
    assert "get_system_status" in tool_names
    assert "read_file" in tool_names
    assert "write_file" in tool_names
    assert "delete_file" in tool_names
    assert "launch_application" in tool_names


def test_file_manager_safe_operations_with_undo(tmp_path):
    """Ensure file operations enforce backups for modifications and deletions."""
    backup_dir = tmp_path / "backups"
    work_dir = tmp_path / "workspace"
    work_dir.mkdir(parents=True, exist_ok=True)

    policy = PathPolicy(allowed_roots=[work_dir])
    mgr = FileManager(backup_dir=backup_dir, policy=policy)

    target_file = work_dir / "note.txt"

    # 1. Write new file (no backup needed since it didn't exist)
    res_write1 = mgr.write_file(target_file, "First revision content")
    assert res_write1["success"] is True
    assert res_write1["backup_path"] is None
    assert target_file.read_text(encoding="utf-8") == "First revision content"

    # 2. Overwrite file -> must create an automated backup
    res_write2 = mgr.write_file(target_file, "Second revision content")
    assert res_write2["success"] is True
    assert res_write2["backup_path"] is not None
    backup_file = Path(res_write2["backup_path"])
    assert backup_file.exists()
    assert backup_file.read_text(encoding="utf-8") == "First revision content"
    assert target_file.read_text(encoding="utf-8") == "Second revision content"

    # 3. Read file
    res_read = mgr.read_file(target_file)
    assert res_read["success"] is True
    assert "Second revision" in res_read["content"]

    # 4. Delete file -> must create backup before deleting
    res_del = mgr.delete_file(target_file)
    assert res_del["success"] is True
    assert not target_file.exists()
    del_backup = Path(res_del["backup_path"])
    assert del_backup.exists()
    assert del_backup.read_text(encoding="utf-8") == "Second revision content"


def test_execution_manager_autonomy_and_approval():
    """Ensure ExecutionManager allows low-risk actions and flags high-impact actions for approval."""
    registry = ToolRegistry()
    register_default_tools(registry)
    perm = PermissionsEngine(mode=AutonomyMode.APPROVED_AUTONOMY)
    exec_mgr = ExecutionManager(registry=registry, permissions=perm)

    # 1. Low-risk execution: get_system_status
    res_status = exec_mgr.execute_tool("get_system_status", {})
    assert res_status["success"] is True
    assert "cpu_percent" in res_status["data"]
    assert res_status["verified"] is True

    # 2. High-impact action without confirmation: lock_workstation
    res_lock = exec_mgr.execute_tool("lock_workstation", {})
    assert res_lock["success"] is False
    assert res_lock.get("approval_required") is True
    assert "approval_id" in res_lock

    # 3. Confirming approval executes action
    approval_id = res_lock["approval_id"]
    perm.resolve_approval(approval_id, approved=True)

    # 4. Emergency Stop blocks all tool executions
    perm.trigger_emergency_stop("Safety check")
    res_blocked = exec_mgr.execute_tool("get_system_status", {})
    assert res_blocked["success"] is False
    assert "Emergency stop is active" in res_blocked["error"]


def test_close_application_and_close_window():
    """Verify close_application and close_active_window execution and schemas."""
    from app.desktop.application_launcher import app_launcher
    from app.desktop.windows_controller import windows_controller

    # 1. Test close application execution
    res_close_app = app_launcher.close("notepad")
    assert res_close_app["success"] is True
    assert res_close_app["action"] == "closed"
    assert res_close_app["display_name"] == "Notepad"

    # 2. Test close active window
    res_close_win = windows_controller.close_active_window()
    assert res_close_win is True

