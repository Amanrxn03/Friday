"""Unit tests for Phase 2: AI Provider Hub, Local Ollama, Cloud Adapters, and Task Planner."""

import pytest
from unittest.mock import MagicMock, patch
from typing import Generator

from app.ai.base_provider import BaseAIProvider, AIResponse, ToolCall
from app.ai.provider_manager import ProviderManager
from app.core.task_planner import TaskPlanner, FRIDAY_SYSTEM_PROMPT
from app.memory.database import Database
from app.memory.task_repository import TaskRepository, TaskStatus
from app.memory.memory_service import MemoryService


class MockProvider(BaseAIProvider):
    """Mock provider for deterministic testing without external API calls."""

    def __init__(self, name: str, available: bool = True, canned_response: str = "Mock response"):
        super().__init__(name=name, default_model="mock-v1")
        self._available = available
        self.canned_response = canned_response

    def is_available(self) -> bool:
        return self._available

    def generate(self, messages, tools=None, model=None, temperature=0.7, max_tokens=4096) -> AIResponse:
        if not self._available:
            return AIResponse(content="", provider_name=self.name, error="Mock provider is offline")
        return AIResponse(
            content=self.canned_response,
            provider_name=self.name,
            model_name="mock-v1",
            prompt_tokens=10,
            completion_tokens=20,
        )

    def stream_generate(self, messages, tools=None, model=None, temperature=0.7, max_tokens=4096) -> Generator[str, None, AIResponse]:
        yield self.canned_response
        return AIResponse(content=self.canned_response, provider_name=self.name)


def test_provider_manager_routing_and_fallback():
    """Ensure ProviderManager routes to active provider and falls back when primary is down."""
    pm = ProviderManager()
    mock_primary = MockProvider("primary", available=False)
    mock_fallback = MockProvider("fallback", available=True, canned_response="Hello from fallback")

    pm.providers = {
        "primary": mock_primary,
        "fallback": mock_fallback,
    }
    pm.active_provider_name = "primary"

    # With fallback enabled, it should detect primary is down and route to fallback
    resp = pm.generate([{"role": "user", "content": "Hi"}], fallback=True)
    assert resp.error is None
    assert resp.content == "Hello from fallback"
    assert resp.provider_name == "fallback"


def test_vram_aware_model_recommendations():
    """Ensure local model recommendations reflect available GPU VRAM (8GB RTX 4070 Laptop)."""
    pm = ProviderManager()
    recs_8gb = pm.get_recommended_local_models(vram_gb=8.0)
    model_names = [r["model"] for r in recs_8gb]
    assert "llama3.2:3b" in model_names
    assert "qwen2.5-coder:7b" in model_names

    # Test lower VRAM budget (e.g. CPU or 4GB)
    recs_4gb = pm.get_recommended_local_models(vram_gb=4.0)
    names_4gb = [r["model"] for r in recs_4gb]
    assert "llama3.2:1b" in names_4gb


def test_task_planner_decomposition(tmp_path):
    """Ensure TaskPlanner breaks goals into tasks and records checkpoints."""
    test_db = Database(db_path=tmp_path / "planner_test.db")
    test_repo = TaskRepository(database=test_db)
    test_mem = MemoryService(database=test_db)

    # Store preference to test memory injection
    test_mem.remember("preferred_language", "Python", is_verified=True)

    canned_plan = """
    {
      "title": "Build Data Pipeline",
      "description": "Construct ETL pipeline with test harness",
      "priority": "HIGH",
      "estimated_minutes": 45,
      "steps": [
        {"index": 1, "description": "Inspect source CSV files", "suggested_tool": "search_files"},
        {"index": 2, "description": "Run schema validation tests", "suggested_tool": "run_tests"}
      ],
      "conversational_summary": "I have mapped out the pipeline steps. Let's begin with inspecting the CSV files."
    }
    """
    mock_ai = MockProvider("mock_smart", available=True, canned_response=canned_plan)
    pm = ProviderManager()
    pm.providers["mock_smart"] = mock_ai
    pm.active_provider_name = "mock_smart"

    planner = TaskPlanner(ai_manager=pm, task_repo=test_repo, mem_service=test_mem)

    # Verify context injection
    context = planner.build_system_context()
    assert "preferred_language: Python" in context
    assert "FRIDAY" in context

    # Run planner
    result = planner.plan_task("Create automated data ingestion pipeline")
    assert result["title"] == "Build Data Pipeline"
    assert result["priority"] == "HIGH"
    assert result["steps_count"] == 2
    assert "I have mapped out" in result["summary"]

    # Verify database persistence
    saved_task = test_repo.get_task(result["task_id"])
    assert saved_task is not None
    assert saved_task.status == TaskStatus.PENDING
    assert len(saved_task.steps) == 2
    assert saved_task.steps[0].description == "Inspect source CSV files"
