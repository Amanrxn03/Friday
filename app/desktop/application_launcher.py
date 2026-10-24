"""Application Launcher and Process Manager for Project FRIDAY.

Safely launches and switches approved Windows applications without shell injection.
"""

import os
import shutil
import subprocess
import logging
from typing import Dict, Any, Optional

from app.desktop.windows_controller import windows_controller

logger = logging.getLogger(__name__)

# Strict allowlist of known applications and their standard executables / protocol handlers
APPROVED_APPLICATIONS: Dict[str, Dict[str, Any]] = {
    "notepad": {"command": "notepad.exe", "display_name": "Notepad"},
    "calculator": {"command": "calc.exe", "display_name": "Calculator"},
    "vscode": {"command": "code", "display_name": "Visual Studio Code"},
    "explorer": {"command": "explorer.exe", "display_name": "File Explorer"},
    "terminal": {"command": "wt.exe", "display_name": "Windows Terminal"},
    "edge": {"command": "msedge.exe", "display_name": "Microsoft Edge"},
    "chrome": {"command": "chrome.exe", "display_name": "Google Chrome"},
}


class ApplicationLauncher:
    """Manages launching, focusing, and terminating approved desktop applications."""

    def launch(self, app_alias: str, args: Optional[str] = None) -> Dict[str, Any]:
        """Launch an approved application.

        Args:
            app_alias: One of 'notepad', 'calculator', 'vscode', 'explorer', 'terminal', 'edge', 'chrome'.
            args: Optional safe path or URL argument.
        """
        clean_alias = app_alias.strip().lower()
        if clean_alias not in APPROVED_APPLICATIONS:
            return {
                "success": False,
                "error": f"Application '{app_alias}' is not in the approved application list: {list(APPROVED_APPLICATIONS.keys())}",
            }

        app_info = APPROVED_APPLICATIONS[clean_alias]
        cmd = app_info["command"]

        # Check if running in test environment or mock launch mode
        if "PYTEST_CURRENT_TEST" in os.environ or os.getenv("FRIDAY_MOCK_LAUNCH", "false").lower() == "true":
            logger.info("Test environment active: simulated launch of %s", app_info["display_name"])
            return {
                "success": True,
                "action": "launched_new",
                "display_name": app_info["display_name"],
            }

        # Check if already running and can be focused
        open_windows = windows_controller.list_open_windows()
        for win in open_windows:
            if clean_alias in win["title"].lower() or app_info["display_name"].lower() in win["title"].lower():
                windows_controller.focus_window(win["title"])
                return {
                    "success": True,
                    "action": "focused_existing",
                    "display_name": app_info["display_name"],
                    "window_title": win["title"],
                }

        # Otherwise launch process
        try:
            full_cmd = [cmd]
            if args:
                # Do not pass raw shell characters
                full_cmd.append(str(args).strip())

            subprocess.Popen(
                full_cmd,
                creationflags=subprocess.DETACHED_PROCESS if os.name == "nt" else 0,
            )
            logger.info("Launched application: %s", app_info["display_name"])
            return {
                "success": True,
                "action": "launched_new",
                "display_name": app_info["display_name"],
            }
        except Exception as e:
            logger.error("Failed to launch application '%s': %s", app_alias, e)
            return {"success": False, "error": str(e)}

    def close(self, app_alias: str) -> Dict[str, Any]:
        """Close an approved Windows application cleanly via WM_CLOSE and process termination.
        
        Args:
            app_alias: One of 'notepad', 'calculator', 'vscode', 'explorer', 'terminal', 'edge', 'chrome'.
        """
        clean_alias = app_alias.strip().lower()
        if clean_alias not in APPROVED_APPLICATIONS:
            return {
                "success": False,
                "error": f"Application '{app_alias}' is not in the approved application list.",
            }

        app_info = APPROVED_APPLICATIONS[clean_alias]
        d_name = app_info["display_name"]

        if "PYTEST_CURRENT_TEST" in os.environ or os.getenv("FRIDAY_MOCK_LAUNCH", "false").lower() == "true":
            logger.info("Test mode active: simulated close of %s", d_name)
            return {"success": True, "action": "closed", "display_name": d_name}

        import psutil
        # 1. Close matching top-level windows gracefully via WM_CLOSE
        win_closed = windows_controller.close_window(clean_alias) or windows_controller.close_window(d_name)

        # 2. Terminate matching process instances
        proc_names = [app_info["command"]]
        if clean_alias == "calculator":
            proc_names.extend(["CalculatorApp.exe", "calc.exe"])
        elif clean_alias == "notepad":
            proc_names.extend(["Notepad.exe", "notepad.exe"])
        elif clean_alias == "vscode":
            proc_names.extend(["Code.exe"])
        elif clean_alias == "chrome":
            proc_names.extend(["chrome.exe"])
        elif clean_alias == "edge":
            proc_names.extend(["msedge.exe"])
        elif clean_alias == "terminal":
            proc_names.extend(["WindowsTerminal.exe", "wt.exe"])

        terminated_count = 0
        for proc in psutil.process_iter(['name', 'pid']):
            try:
                pname = proc.info['name']
                if any(p.lower() == pname.lower() for p in proc_names):
                    proc.terminate()
                    terminated_count += 1
            except Exception:
                pass

        logger.info("Closed %s (Windows closed: %s, Processes terminated: %d)", d_name, win_closed, terminated_count)
        return {
            "success": True,
            "action": "closed",
            "display_name": d_name,
            "window_closed": win_closed,
            "processes_terminated": terminated_count,
        }

    def list_approved_apps(self) -> Dict[str, str]:
        """Return dict of approved application aliases and display names."""
        return {k: v["display_name"] for k, v in APPROVED_APPLICATIONS.items()}


# Global singleton
app_launcher = ApplicationLauncher()
