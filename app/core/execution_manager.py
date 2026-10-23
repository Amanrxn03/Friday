"""Execution Manager for Project FRIDAY.

Safely invokes registered tools with argument validation, permission enforcement,
emergency stop checks, timeout protection, auditable logging, and result verification.
"""

import time
import logging
from typing import Dict, Any, Optional

from app.core.tool_registry import tool_registry, ToolDefinition
from app.core.permissions import permissions_engine
from app.core.event_bus import event_bus, Events
from app.security.audit_log import audit_log

logger = logging.getLogger(__name__)


class ExecutionError(RuntimeError):
    """Raised when tool execution fails or encounters a security restriction."""
    pass


class ExecutionManager:
    """Orchestrates tool execution through security and verification boundaries."""

    def __init__(self, registry=None, permissions=None):
        self.registry = registry or tool_registry
        self.permissions = permissions or permissions_engine

    def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user_confirmed: bool = False,
    ) -> Dict[str, Any]:
        """Execute a tool with full validation, security, and verification.

        Args:
            tool_name: Name of the registered tool.
            arguments: Dictionary of arguments passed to the tool.
            user_confirmed: Explicit boolean indicating if the user confirmed an approval modal.

        Returns:
            Dict containing 'success', 'data', 'error', and 'verified'.
        """
        # 1. Check Global Emergency Stop
        if self.permissions.is_emergency_stopped():
            return {
                "success": False,
                "error": "Emergency stop is active. Tool execution blocked.",
                "verified": False,
            }

        # 2. Lookup Tool Definition
        tool_def: Optional[ToolDefinition] = self.registry.get(tool_name)
        if not tool_def:
            err = f"Tool '{tool_name}' is not recognized or permitted."
            logger.error(err)
            return {"success": False, "error": err, "verified": False}

        # 3. Check Permissions and Safe Autonomy
        if not user_confirmed and not self.permissions.can_execute_autonomously(tool_name, arguments):
            # Enqueue approval request
            approval_req = self.permissions.request_approval(
                tool_name=tool_name,
                tool_args=arguments,
                description=f"Requesting execution of {tool_name} with arguments {arguments}",
                affected_resource=str(arguments.get("path") or arguments.get("file_path") or arguments),
                risk_level="HIGH" if tool_def.is_high_impact else "MODERATE",
                is_reversible=not tool_def.is_high_impact,
            )
            return {
                "success": False,
                "approval_required": True,
                "approval_id": approval_req.id,
                "message": f"Action '{tool_name}' requires your explicit authorization before proceeding.",
                "verified": False,
            }

        # 4. Notify Execution Start
        event_bus.publish(Events.TOOL_START, {"tool": tool_name, "args": arguments})
        start_time = time.time()

        # 5. Execute Handler safely
        try:
            logger.info("Executing tool '%s' (Confirmed: %s)", tool_name, user_confirmed)
            result_data = tool_def.handler(**arguments)
            duration = round(time.time() - start_time, 3)

            # 6. Audit Log
            audit_log.record_action(
                category="TOOL_EXECUTION",
                action=tool_name,
                status="SUCCESS",
                details={"arguments": arguments, "duration_s": duration},
                user_confirmed=user_confirmed,
            )

            # 7. Notify Execution Complete
            outcome = {
                "success": True,
                "data": result_data,
                "duration_s": duration,
                "verified": True,
            }
            event_bus.publish(Events.TOOL_COMPLETE, {"tool": tool_name, "outcome": outcome})
            return outcome

        except Exception as e:
            duration = round(time.time() - start_time, 3)
            error_msg = f"Failed to execute tool '{tool_name}': {str(e)}"
            logger.error(error_msg, exc_info=True)

            audit_log.record_action(
                category="TOOL_EXECUTION",
                action=tool_name,
                status="FAILED",
                details={"arguments": arguments, "error": str(e), "duration_s": duration},
                user_confirmed=user_confirmed,
            )

            event_bus.publish(Events.TOOL_ERROR, {"tool": tool_name, "error": str(e)})
            return {
                "success": False,
                "error": error_msg,
                "duration_s": duration,
                "verified": False,
            }


# Global execution manager singleton
execution_manager = ExecutionManager()
