"""Windows Startup Registration Service for Project FRIDAY.

Manages automatic launch on Windows login via the Current User Registry Run key
without requiring administrator privileges.
"""

import sys
import os
import logging
from pathlib import Path
from typing import Optional

try:
    import winreg
    WINREG_AVAILABLE = True
except Exception:
    WINREG_AVAILABLE = False

logger = logging.getLogger(__name__)

REG_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
REG_APP_NAME = "ProjectFRIDAY"


class StartupService:
    """Configures Windows automatic startup registration."""

    def is_startup_enabled(self) -> bool:
        """Check if FRIDAY is currently registered in HKCU Run."""
        if not WINREG_AVAILABLE or os.name != "nt":
            return False

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, REG_APP_NAME)
                return bool(val)
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.warning("Error reading Windows startup registry: %s", e)
            return False

    def enable_startup(self, executable_path: Optional[str] = None) -> bool:
        """Register FRIDAY to launch automatically upon Windows user logon."""
        if not WINREG_AVAILABLE or os.name != "nt":
            return False

        if not executable_path:
            # Default to run_friday.bat in the project root
            root_dir = Path(__file__).resolve().parent.parent.parent
            batch_launcher = root_dir / "run_friday.bat"
            if batch_launcher.exists():
                executable_path = f'"{batch_launcher}"'
            else:
                # Python interpreter running main.py
                python_exe = sys.executable
                main_py = root_dir / "app" / "main.py"
                executable_path = f'"{python_exe}" "{main_py}"'

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, REG_APP_NAME, 0, winreg.REG_SZ, executable_path)
            logger.info("Windows Startup enabled with command: %s", executable_path)
            return True
        except Exception as e:
            logger.error("Failed to set Windows startup registry key: %s", e)
            return False

    def disable_startup(self) -> bool:
        """Remove FRIDAY from Windows startup registry."""
        if not WINREG_AVAILABLE or os.name != "nt":
            return False

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, REG_APP_NAME)
            logger.info("Windows Startup registration removed.")
            return True
        except FileNotFoundError:
            return True  # Already disabled
        except Exception as e:
            logger.error("Failed to delete Windows startup registry key: %s", e)
            return False


# Global singleton
startup_service = StartupService()
