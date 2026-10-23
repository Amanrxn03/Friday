"""Permissions Engine and Safe Autonomy Guard for Project FRIDAY.

Enforces execution policies, manages user approval queues for high-impact actions,
and provides an immediate Global Emergency Stop.
"""

import uuid
import threading
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Set

from app.config import config, AutonomyMode
from app.core.event_bus import event_bus, Events
from app.security.audit_log import audit_log

logger = logging.getLogger(__name__)


# Explicit set of inherently high-impact tool operations that ALWAYS require confirmation
HIGH_IMPACT_TOOLS: Set[str] = {
    "delete_file",
    "delete_folder",
    "overwrite_file",
    "execute_system_command",
    "run_terminal_command",
    "send_email",
    "post_external_message",
    "install_package",
    "modify_security_setting",
    "lock_workstation",
}

# Low-risk tools allowed to run independently in APPROVED_AUTONOMY mode
LOW_RISK_READ_TOOLS: Set[str] = {
    "list_directory",
    "read_file",
    "search_files",
    "get_system_status",
    "get_battery_status",
    "list_windows",
    "focus_window",
    "get_weather",
    "get_news",
    "list_tasks",
    "get_task_details",
    "recall_memory",
    "list_memory_items",
}


@dataclass
class ApprovalRequest:
    id: str
    tool_name: str
    tool_args: Dict[str, Any]
    description: str
    risk_level: str  # HIGH, CRITICAL, MODERATE
    affected_resource: str
    is_reversible: bool
    status: str = "PENDING"  # PENDING, APPROVED, REJECTED, EXPIRED
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: Optional[str] = None


class PermissionsEngine:
    """Evaluates whether an action can execute autonomously or must wait for user approval."""

    def __init__(self, mode: Optional[AutonomyMode] = None):
        self.mode = mode or config.autonomy_mode
        self._emergency_stopped = False
        self._pending_approvals: Dict[str, ApprovalRequest] = {}
        self._lock = threading.RLock()

    # --- Emergency Stop ---
    def trigger_emergency_stop(self, reason: str = "User initiated emergency stop") -> None:
        """Immediately halt all pending and ongoing automation."""
        with self._lock:
            self._emergency_stopped = True
            # Reject all pending approvals
            for req in self._pending_approvals.values():
                if req.status == "PENDING":
                    req.status = "REJECTED"
                    req.resolved_at = datetime.now(timezone.utc).isoformat()

        logger.critical("EMERGENCY STOP TRIGGERED: %s", reason)
        audit_log.record_action(
            category="SECURITY",
            action="EMERGENCY_STOP",
            status="TRIGGERED",
            details={"reason": reason},
        )
        event_bus.publish(Events.EMERGENCY_STOP, {"reason": reason})

    def reset_emergency_stop(self) -> None:
        """Reset emergency stop state after user verification."""
        with self._lock:
            self._emergency_stopped = False
        logger.warning("Emergency stop has been RESET by user.")
        audit_log.record_action(
            category="SECURITY",
            action="EMERGENCY_RESET",
            status="RESET",
        )
        event_bus.publish(Events.EMERGENCY_RESET)

    def is_emergency_stopped(self) -> bool:
        with self._lock:
            return self._emergency_stopped

    # --- Mode Management ---
    def set_autonomy_mode(self, mode: AutonomyMode) -> None:
        """Update autonomy mode."""
        self.mode = mode
        logger.info("FRIDAY Autonomy Mode changed to: %s", mode.value)
        audit_log.record_action(
            category="CONFIG",
            action="CHANGE_AUTONOMY_MODE",
            status="SUCCESS",
            details={"new_mode": mode.value},
            user_confirmed=True,
        )

    # --- Impact Evaluation ---
    def is_high_impact(self, tool_name: str, args: Optional[Dict[str, Any]] = None) -> bool:
        """Determine whether a tool invocation constitutes a high-impact action."""
        tool_clean = tool_name.strip().lower()

        if tool_clean in HIGH_IMPACT_TOOLS:
            return True

        # Check for conditional high impact (e.g., file write that might overwrite existing file)
        if tool_clean == "write_file":
            args = args or {}
            target_path = args.get("file_path") or args.get("path")
            if target_path:
                import os
                if os.path.exists(target_path):
                    return True  # Overwrite of existing file is high-impact

        return False

    def can_execute_autonomously(self, tool_name: str, args: Optional[Dict[str, Any]] = None) -> bool:
        """Check if action is authorized to execute immediately without a modal prompt."""
        if self._emergency_stopped:
            return False

        tool_clean = tool_name.strip().lower()

        # Mode 1: SUGGEST -> Everything requires approval
        if self.mode == AutonomyMode.SUGGEST:
            return False

        # Mode 2: APPROVED_AUTONOMY -> Low risk can run; high-impact requires confirmation
        if self.mode == AutonomyMode.APPROVED_AUTONOMY:
            if self.is_high_impact(tool_clean, args):
                return False
            return True

        # Mode 3: CONFIRM_HIGH_IMPACT -> High impact always requires confirmation
        if self.mode == AutonomyMode.CONFIRM_HIGH_IMPACT:
            if self.is_high_impact(tool_clean, args):
                return False
            return True

        return False

    # --- Approval Queue ---
    def request_approval(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        description: str,
        affected_resource: str = "",
        risk_level: str = "HIGH",
        is_reversible: bool = False,
    ) -> ApprovalRequest:
        """Register a pending action in the approval queue and broadcast event."""
        if self._emergency_stopped:
            raise PermissionError("Cannot request approval while Emergency Stop is active.")

        req_id = str(uuid.uuid4())[:8]
        req = ApprovalRequest(
            id=req_id,
            tool_name=tool_name,
            tool_args=tool_args,
            description=description,
            risk_level=risk_level,
            affected_resource=affected_resource or str(tool_args),
            is_reversible=is_reversible,
            status="PENDING",
        )

        with self._lock:
            self._pending_approvals[req_id] = req

        logger.warning(
            "Approval required for tool '%s' (ID: %s): %s", tool_name, req_id, description
        )
        event_bus.publish(Events.APPROVAL_REQUIRED, req)
        return req

    def resolve_approval(self, req_id: str, approved: bool) -> bool:
        """Resolve a pending approval request with user's decision."""
        with self._lock:
            req = self._pending_approvals.get(req_id)
            if not req or req.status != "PENDING":
                return False

            req.status = "APPROVED" if approved else "REJECTED"
            req.resolved_at = datetime.now(timezone.utc).isoformat()

        audit_log.record_action(
            category="APPROVAL",
            action=req.tool_name,
            status="APPROVED" if approved else "REJECTED",
            details={"request_id": req_id, "args": req.tool_args},
            user_confirmed=True,
        )

        event_bus.publish(Events.APPROVAL_RESOLVED, req)
        return approved

    def get_pending_approvals(self) -> List[ApprovalRequest]:
        with self._lock:
            return [req for req in self._pending_approvals.values() if req.status == "PENDING"]


# Global permissions engine singleton
permissions_engine = PermissionsEngine()
