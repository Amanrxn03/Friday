"""Unit and integration tests for Phase 1 foundation: Config, Security, Memory, and Permissions."""

import os
import tempfile
from pathlib import Path
import pytest

from app.config import FridayConfig, AutonomyMode
from app.security.secret_store import SecretStore
from app.security.audit_log import redact_sensitive_data
from app.security.path_policy import PathPolicy, PathPolicyError
from app.memory.database import Database
from app.memory.task_repository import TaskRepository, TaskPriority, TaskStatus
from app.memory.memory_service import MemoryService
from app.core.event_bus import EventBus, Events
from app.core.permissions import PermissionsEngine, ApprovalRequest


def test_sensitive_data_redaction():
    """Ensure API keys and tokens are automatically redacted."""
    raw = "Failed with OpenAI sk-abcdef123456789012345678 and Anthropic sk-ant-api03-abcdef123456789012345678"
    sanitized = redact_sensitive_data(raw)
    assert "sk-abcdef" not in sanitized
    assert "sk-ant-" not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized
    assert "[REDACTED_ANTHROPIC_KEY]" in sanitized


def test_path_policy_traversal_prevention():
    """Ensure path policy strictly forbids path traversal and system directory access."""
    with tempfile.TemporaryDirectory() as temp_root:
        root_path = Path(temp_root)
        policy = PathPolicy(allowed_roots=[root_path])

        safe_file = root_path / "test.txt"
        assert policy.validate_path(safe_file) == safe_file.resolve()

        # Try to escape root using traversal
        traversal_path = root_path / ".." / "outside.txt"
        with pytest.raises(PathPolicyError):
            policy.validate_path(traversal_path)

        # Try to access Windows directory
        with pytest.raises(PathPolicyError):
            policy.validate_path("C:\\Windows\\System32\\cmd.exe")


def test_database_and_task_checkpoints():
    """Ensure task persistence, step checkpointing, and status updates work atomically."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_db_path = Path(temp_dir) / "test_friday.db"
        db = Database(db_path=test_db_path)
        repo = TaskRepository(database=db)

        # Create Task
        task = repo.create_task(
            title="Inspect System Status",
            description="Collect CPU and RAM metrics",
            priority=TaskPriority.HIGH,
            estimated_minutes=15,
        )
        assert task.id is not None
        assert task.title == "Inspect System Status"
        assert task.status == TaskStatus.PENDING

        # Add Steps
        step1 = repo.add_step(
            task_id=task.id,
            step_index=1,
            description="Query CPU usage",
            tool_name="get_system_status",
            tool_args={"metric": "cpu"},
        )
        assert step1.id is not None

        # Checkpoint Step
        repo.update_step_result(
            task_id=task.id,
            step_index=1,
            status="COMPLETED",
            result={"cpu_percent": 12.5},
        )

        # Update Task status
        repo.update_task_status(task_id=task.id, status=TaskStatus.IN_PROGRESS, progress_percent=50)

        # Retrieve and verify
        reloaded = repo.get_task(task.id)
        assert reloaded is not None
        assert reloaded.progress_percent == 50
        assert len(reloaded.steps) == 1
        assert reloaded.steps[0].status == "COMPLETED"
        assert reloaded.steps[0].result == {"cpu_percent": 12.5}


def test_memory_service_explicit_vs_inferred():
    """Ensure explicit facts and inferred preferences are stored with accurate distinction."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_db_path = Path(temp_dir) / "test_mem.db"
        db = Database(db_path=test_db_path)
        mem = MemoryService(database=db)

        # Explicit user fact
        mem.remember("editor", "VS Code", category="preference", is_verified=True)
        # Inferred preference
        mem.remember("speech_speed_preference", "slightly_fast", category="preference", is_verified=False)

        assert mem.recall("editor") == "VS Code"
        items = mem.list_items(category="preference")
        assert len(items) == 2

        verified_map = {item.key: item.is_verified for item in items}
        assert verified_map["editor"] is True
        assert verified_map["speech_speed_preference"] is False

        # Test Privacy Mode
        mem.set_privacy_mode(True)
        mem.remember("temporary_key", "temporary_value")
        assert mem.recall("temporary_key") is None


def test_permissions_and_emergency_stop():
    """Ensure autonomy modes and emergency stop operate correctly."""
    perm = PermissionsEngine(mode=AutonomyMode.APPROVED_AUTONOMY)

    # Low risk read should execute autonomously
    assert perm.can_execute_autonomously("read_file") is True

    # High impact action must require confirmation
    assert perm.can_execute_autonomously("delete_file") is False

    # Mode 1: SUGGEST -> Everything requires approval
    perm.set_autonomy_mode(AutonomyMode.SUGGEST)
    assert perm.can_execute_autonomously("read_file") is False

    # Emergency stop blocks everything immediately
    perm.set_autonomy_mode(AutonomyMode.APPROVED_AUTONOMY)
    perm.trigger_emergency_stop("Safety test")
    assert perm.is_emergency_stopped() is True
    assert perm.can_execute_autonomously("read_file") is False

    perm.reset_emergency_stop()
    assert perm.is_emergency_stopped() is False
    assert perm.can_execute_autonomously("read_file") is True
