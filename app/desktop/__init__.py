"""Desktop automation and system control subsystem for Project FRIDAY."""

from app.desktop.windows_controller import WindowsController, windows_controller
from app.desktop.application_launcher import ApplicationLauncher, app_launcher
from app.desktop.file_manager import FileManager, file_manager
from app.desktop.browser_automation import BrowserAutomation, browser_automation

__all__ = [
    "WindowsController",
    "windows_controller",
    "ApplicationLauncher",
    "app_launcher",
    "FileManager",
    "file_manager",
    "BrowserAutomation",
    "browser_automation",
]
