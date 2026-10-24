"""Unit and UI smoke tests for Services, Briefing, Startup, and PySide6 widgets."""

import os
import pytest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication

from app.services.news_service import NewsService
from app.services.briefing_service import BriefingService
from app.services.startup_service import StartupService
from app.memory.database import Database
from app.memory.task_repository import TaskRepository, TaskPriority
from app.memory.memory_service import MemoryService
from app.core.permissions import ApprovalRequest


@pytest.fixture(scope="session")
def qapp():
    """Ensure QApplication is initialized for UI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_news_and_weather_service():
    """Ensure NewsService fetches or falls back gracefully without unhandled exceptions."""
    svc = NewsService(timeout=3)
    weather = svc.get_weather("Bengaluru")
    assert "city" in weather
    assert weather["city"] == "Bengaluru"


def test_briefing_service(tmp_path):
    """Ensure BriefingService synthesizes tasks, weather, and conversational greeting."""
    test_db = Database(db_path=tmp_path / "briefing_test.db")
    test_tasks = TaskRepository(database=test_db)
    test_mem = MemoryService(database=test_db)

    # Add a task to be summarized
    test_tasks.create_task(title="Deploy Release v1.0", priority=TaskPriority.HIGH)

    mock_news = MagicMock()
    mock_news.get_weather.return_value = {"city": "Bengaluru", "temperature_c": 24.5, "wind_speed_kmh": 12}
    mock_news.get_full_briefing_news.return_value = {"India National": []}

    bs = BriefingService(task_repo=test_tasks, mem_service=test_mem, news_svc=mock_news)
    briefing = bs.generate_morning_briefing()

    assert "greeting" in briefing
    assert "FRIDAY is online" in briefing["greeting"]
    assert "Deploy Release v1.0" in briefing["greeting"]
    assert len(briefing["tasks"]) == 1


def test_startup_service():
    """Ensure StartupService methods can be called without unhandled exceptions."""
    svc = StartupService()
    # Read status should return boolean
    enabled = svc.is_startup_enabled()
    assert isinstance(enabled, bool)


def test_ui_components_smoke_test(qapp):
    """Instantiate core PySide6 UI windows offscreen to ensure no layout or attribute errors."""
    from app.ui.main_window import MainWindow
    from app.ui.compact_hud import CompactHUD
    from app.ui.widgets.approval_dialog import ApprovalDialog

    window = MainWindow()
    assert "FRIDAY" in window.windowTitle() and "Personal AI Desktop Companion" in window.windowTitle()

    hud = CompactHUD(main_window=window)
    assert hud.width() == 540

    mock_req = ApprovalRequest(
        id="test_req",
        tool_name="delete_file",
        tool_args={"file_path": "c:\\test.txt"},
        description="Delete test file",
        risk_level="HIGH",
        affected_resource="c:\\test.txt",
        is_reversible=False,
    )
    dialog = ApprovalDialog(mock_req, window)
    assert dialog.windowTitle().startswith("Security Authorization")

    window.close()
    hud.close()
    dialog.close()
