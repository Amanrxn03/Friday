"""Tool Registry for Project FRIDAY.

Defines schemas, risk categories, handlers, and parameter validation for all desktop,
file, system, memory, and productivity tools.
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, Any, List, Optional
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema format
    handler: Callable[..., Any]
    is_high_impact: bool = False
    requires_approval_in_modes: List[str] = field(default_factory=lambda: ["SUGGEST", "CONFIRM_HIGH_IMPACT"])


class ToolRegistry:
    """Central registry for all tools accessible by FRIDAY."""

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable[..., Any],
        is_high_impact: bool = False,
    ) -> None:
        """Register a tool callable with its JSON schema and impact classification."""
        self._tools[name] = ToolDefinition(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
            is_high_impact=is_high_impact,
        )
        logger.debug("Registered tool: %s (High Impact: %s)", name, is_high_impact)

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_all(self) -> List[ToolDefinition]:
        return list(self._tools.values())

    def get_openai_tool_schemas(self) -> List[Dict[str, Any]]:
        """Export tool specifications in OpenAI / Ollama function calling JSON Schema format."""
        schemas = []
        for tool in self._tools.values():
            schemas.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                }
            })
        return schemas


def register_default_tools(registry: ToolRegistry) -> None:
    """Populate registry with core Windows, file, memory, and web automation tools."""
    from app.desktop.windows_controller import windows_controller
    from app.desktop.application_launcher import app_launcher
    from app.desktop.file_manager import file_manager
    from app.desktop.browser_automation import browser_automation
    from app.memory.memory_service import memory_service
    from app.memory.task_repository import task_repository

    # 1. System Status
    registry.register(
        name="get_system_status",
        description="Inspect Windows system metrics including CPU, RAM, Disk, and Battery.",
        parameters={"type": "object", "properties": {}},
        handler=windows_controller.get_system_status,
        is_high_impact=False,
    )

    # 1b. Current System Time
    def _get_system_time() -> Dict[str, Any]:
        import datetime
        now = datetime.datetime.now()
        return {
            "time": now.strftime("%I:%M %p"),
            "date": now.strftime("%A, %B %d, %Y"),
            "timestamp": now.isoformat(),
        }

    registry.register(
        name="get_current_time",
        description="Get current local time, date, and day of week.",
        parameters={"type": "object", "properties": {}},
        handler=_get_system_time,
        is_high_impact=False,
    )

    # 2. List Windows
    registry.register(
        name="list_open_windows",
        description="List all visible desktop application windows and their titles.",
        parameters={"type": "object", "properties": {}},
        handler=windows_controller.list_open_windows,
        is_high_impact=False,
    )

    # 3. Focus Window
    registry.register(
        name="focus_window",
        description="Bring an open window matching the given title query to the foreground.",
        parameters={
            "type": "object",
            "properties": {"title_query": {"type": "string", "description": "Part of the window title to match"}},
            "required": ["title_query"],
        },
        handler=windows_controller.focus_window,
        is_high_impact=False,
    )

    # 4. Adjust Volume
    registry.register(
        name="adjust_system_volume",
        description="Set the master Windows system audio volume (0 to 100).",
        parameters={
            "type": "object",
            "properties": {"level_percent": {"type": "integer", "description": "Volume percentage from 0 to 100"}},
            "required": ["level_percent"],
        },
        handler=windows_controller.adjust_system_volume,
        is_high_impact=False,
    )

    # 5. Lock Workstation
    registry.register(
        name="lock_workstation",
        description="Lock the Windows workstation. Requires explicit confirmation.",
        parameters={"type": "object", "properties": {}},
        handler=windows_controller.lock_workstation,
        is_high_impact=True,
    )

    # 6. Launch Application
    registry.register(
        name="launch_application",
        description="Launch or focus an approved Windows application (notepad, calculator, vscode, explorer, terminal, edge, chrome).",
        parameters={
            "type": "object",
            "properties": {
                "app_alias": {"type": "string", "description": "App alias: notepad, calculator, vscode, explorer, terminal, edge, chrome"},
                "args": {"type": "string", "description": "Optional file path or URL to open with the application"},
            },
            "required": ["app_alias"],
        },
        handler=app_launcher.launch,
        is_high_impact=False,
    )

    # 7. List Directory
    registry.register(
        name="list_directory",
        description="List files and subdirectories in an authorized directory path.",
        parameters={
            "type": "object",
            "properties": {"dir_path": {"type": "string", "description": "Path to the directory"}},
            "required": ["dir_path"],
        },
        handler=file_manager.list_directory,
        is_high_impact=False,
    )

    # 8. Search Files
    registry.register(
        name="search_files",
        description="Search for files matching a glob pattern (e.g. '*.py', '*report*') within allowed paths.",
        parameters={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Glob search pattern"},
                "search_root": {"type": "string", "description": "Optional directory root to search within"},
            },
            "required": ["pattern"],
        },
        handler=file_manager.search_files,
        is_high_impact=False,
    )

    # 9. Read File
    registry.register(
        name="read_file",
        description="Read the text content of a file within an approved working directory.",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the file to read"},
                "max_chars": {"type": "integer", "description": "Maximum characters to return (default 10000)"},
            },
            "required": ["file_path"],
        },
        handler=file_manager.read_file,
        is_high_impact=False,
    )

    # 10. Write File
    registry.register(
        name="write_file",
        description="Write text content to a file in an authorized directory. Creates automated backup if overwriting.",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Target file path"},
                "content": {"type": "string", "description": "Text content to write"},
            },
            "required": ["file_path", "content"],
        },
        handler=file_manager.write_file,
        is_high_impact=False,  # Overwrites are conditionally flagged by permissions_engine
    )

    # 11. Delete File
    registry.register(
        name="delete_file",
        description="Delete a file within authorized paths. Generates a backup first and requires explicit confirmation.",
        parameters={
            "type": "object",
            "properties": {"file_path": {"type": "string", "description": "Path of file to delete"}},
            "required": ["file_path"],
        },
        handler=file_manager.delete_file,
        is_high_impact=True,
    )

    # 12. Open Website
    registry.register(
        name="open_website",
        description="Open an authorized http/https URL in the user's default web browser.",
        parameters={
            "type": "object",
            "properties": {"url": {"type": "string", "description": "The URL to open"}},
            "required": ["url"],
        },
        handler=browser_automation.open_url,
        is_high_impact=False,
    )

    # 13. Search Web
    registry.register(
        name="search_web",
        description="Perform a web search in the default web browser.",
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query terms"}},
            "required": ["query"],
        },
        handler=browser_automation.search_web,
        is_high_impact=False,
    )

    # 14. Remember Fact
    registry.register(
        name="remember_fact",
        description="Store a long-term user preference, project detail, or verified fact.",
        parameters={
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Semantic identifier for the fact"},
                "value": {"type": "string", "description": "The information to remember"},
                "category": {"type": "string", "description": "Category (preference, project, general)"},
            },
            "required": ["key", "value"],
        },
        handler=lambda key, value, category="general": memory_service.remember(key, value, category, is_verified=True),
        is_high_impact=False,
    )

    # 15. Recall Fact
    registry.register(
        name="recall_fact",
        description="Retrieve a stored fact or user preference by key.",
        parameters={
            "type": "object",
            "properties": {"key": {"type": "string", "description": "Semantic identifier to look up"}},
            "required": ["key"],
        },
        handler=memory_service.recall,
        is_high_impact=False,
    )

    # 16. Set Voice Profile
    from app.voice.text_to_speech import tts_manager
    registry.register(
        name="set_voice_profile",
        description="Switch FRIDAY's speaking voice persona (e.g. 'kriti' for custom cloned voice, 'heera' for Indian English, 'zira' for US English).",
        parameters={
            "type": "object",
            "properties": {
                "profile_id": {
                    "type": "string",
                    "description": "Voice profile identifier ('kriti', 'heera', 'zira', 'david')",
                }
            },
            "required": ["profile_id"],
        },
        handler=lambda profile_id="kriti": (tts_manager.set_voice_profile(profile_id), {"status": "success", "voice_profile": profile_id})[1],
        is_high_impact=False,
    )

    # 17. Play Voice Sample
    registry.register(
        name="play_voice_sample",
        description="Play Kriti's original audio sample or any voice reference file.",
        parameters={
            "type": "object",
            "properties": {
                "sample_path": {
                    "type": "string",
                    "description": "Optional path to the voice sample file",
                }
            },
        },
        handler=lambda sample_path=None: (tts_manager.play_custom_sample(sample_path), {"status": "success", "playing": True})[1],
        is_high_impact=False,
    )



# Global tool registry singleton
tool_registry = ToolRegistry()
register_default_tools(tool_registry)
