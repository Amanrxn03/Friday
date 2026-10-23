"""Windows Controller for Project FRIDAY.

Provides native Windows management including hardware telemetry, open window manipulation,
volume adjustment, and workstation locking via pywin32 and psutil.
"""

import os
import ctypes
import logging
from typing import Dict, Any, List, Optional
import psutil

try:
    import win32gui
    import win32con
    import win32process
    WIN32_AVAILABLE = True
except Exception:
    WIN32_AVAILABLE = False

logger = logging.getLogger(__name__)


class WindowsController:
    """Controls Windows desktop functions and hardware monitoring."""

    def get_system_status(self) -> Dict[str, Any]:
        """Collect current CPU, RAM, Disk, and Battery metrics."""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\")

        battery_info = None
        battery = psutil.sensors_battery()
        if battery:
            battery_info = {
                "percent": battery.percent,
                "power_plugged": battery.power_plugged,
                "secsleft": battery.secsleft if battery.secsleft > 0 else None,
            }

        return {
            "cpu_percent": cpu_percent,
            "ram_total_gb": round(ram.total / (1024**3), 2),
            "ram_used_gb": round(ram.used / (1024**3), 2),
            "ram_percent": ram.percent,
            "disk_c_free_gb": round(disk.free / (1024**3), 2),
            "disk_c_percent": disk.percent,
            "battery": battery_info,
        }

    def list_open_windows(self) -> List[Dict[str, Any]]:
        """Return titles and process information of visible desktop windows."""
        windows = []
        if not WIN32_AVAILABLE:
            return windows

        def enum_handler(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).strip()
                if title:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    try:
                        pname = psutil.Process(pid).name()
                    except Exception:
                        pname = "unknown"
                    windows.append({
                        "hwnd": hwnd,
                        "title": title,
                        "process_name": pname,
                        "pid": pid,
                    })

        try:
            win32gui.EnumWindows(enum_handler, None)
        except Exception as e:
            logger.error("Error enumerating windows: %s", e)

        return windows

    def focus_window(self, title_query: str) -> bool:
        """Bring a window matching title_query to the foreground."""
        if not WIN32_AVAILABLE:
            return False

        query = title_query.strip().lower()
        target_hwnd = None

        def enum_handler(hwnd, _):
            nonlocal target_hwnd
            if target_hwnd is not None:
                return
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).strip().lower()
                if query in title:
                    target_hwnd = hwnd

        try:
            win32gui.EnumWindows(enum_handler, None)
            if target_hwnd:
                # Restore window if minimized
                win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(target_hwnd)
                logger.info("Focused window matching '%s' (HWND: %s)", title_query, target_hwnd)
                return True
        except Exception as e:
            logger.error("Failed to focus window '%s': %s", title_query, e)

        return False

    def adjust_system_volume(self, level_percent: int) -> bool:
        """Set Windows system volume percentage (0 - 100)."""
        clamped = max(0, min(100, int(level_percent)))
        # Execute safe volume dispatcher via Windows virtual key events or PowerShell Audio API
        try:
            # Safe Windows API dispatch
            import subprocess
            cmd = f"$obj = New-Object -ComObject WScript.Shell; 1..50 | % {{ $obj.SendKeys([char]174) }}; 1..{clamped // 2} | % {{ $obj.SendKeys([char]175) }}"
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            logger.info("Adjusted system volume to approximately %d%%", clamped)
            return True
        except Exception as e:
            logger.warning("Could not adjust volume: %s", e)
            return False

    def lock_workstation(self) -> bool:
        """Lock the Windows workstation when explicitly requested."""
        try:
            ctypes.windll.user32.LockWorkStation()
            logger.info("Workstation locked by FRIDAY.")
            return True
        except Exception as e:
            logger.error("Failed to lock workstation: %s", e)
            return False


# Global singleton
windows_controller = WindowsController()
