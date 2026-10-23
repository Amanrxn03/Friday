"""Morning Briefing Service for Project FRIDAY.

Prepares comprehensive daily briefings by synthesizing system health, unfinished tasks,
recent project continuity, verified facts, live weather, and source-backed news headlines.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from app.memory.database import db
from app.memory.task_repository import task_repository, Task
from app.memory.memory_service import memory_service
from app.services.news_service import news_service
from app.ai.provider_manager import provider_manager
from app.core.event_bus import event_bus, Events
from app.config import config

logger = logging.getLogger(__name__)


class BriefingService:
    """Compiles and formats daily startup briefings."""

    def __init__(self, task_repo=None, mem_service=None, news_svc=None):
        self.tasks = task_repo or task_repository
        self.memory = mem_service or memory_service
        self.news = news_svc or news_service

    def generate_morning_briefing(self) -> Dict[str, Any]:
        """Assemble the complete daily briefing."""
        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")

        # 1. Check Unfinished & Pending Tasks
        unfinished_tasks: List[Task] = self.tasks.get_unfinished_tasks()
        task_summaries = [
            {"id": t.id, "title": t.title, "priority": t.priority.value, "progress": t.progress_percent}
            for t in unfinished_tasks
        ]

        # 2. Check Active Projects
        projects = self.memory.list_active_projects()

        # 3. Weather
        weather = self.news.get_weather()

        # 4. News Headlines
        news_data = {}
        if config.briefing.enabled:
            news_data = self.news.get_full_briefing_news(items_per_category=2)

        # 5. Formulate Conversational Spoken Greeting
        greeting_parts = []
        hour = datetime.now().hour
        if hour < 12:
            time_greeting = "Good morning!"
        elif hour < 17:
            time_greeting = "Good afternoon!"
        else:
            time_greeting = "Good evening!"

        greeting_parts.append(f"{time_greeting} FRIDAY is online.")

        if weather and "temperature_c" in weather and weather["temperature_c"] is not None:
            greeting_parts.append(f"It's currently {weather['temperature_c']}°C in {weather['city']}.")

        if unfinished_tasks:
            greeting_parts.append(
                f"You have {len(unfinished_tasks)} active task{'s' if len(unfinished_tasks) > 1 else ''} pending, "
                f"starting with '{unfinished_tasks[0].title}'."
            )
            greeting_parts.append("Would you like to resume where we left off, or start on something new?")
        else:
            greeting_parts.append("Your task queue is clear. What would you like to tackle today?")

        spoken_script = " ".join(greeting_parts)

        # 6. Store in Database
        try:
            query = """
            INSERT INTO daily_briefings (date_str, news_json, weather_summary, task_summary)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(date_str) DO UPDATE SET
                news_json = excluded.news_json,
                weather_summary = excluded.weather_summary,
                task_summary = excluded.task_summary;
            """
            db.execute_write(
                query,
                (
                    today_str,
                    json.dumps(news_data),
                    json.dumps(weather),
                    json.dumps(task_summaries),
                ),
            )
        except Exception as e:
            logger.warning("Could not persist briefing to SQLite: %s", e)

        briefing_payload = {
            "date": today_str,
            "greeting": spoken_script,
            "tasks": task_summaries,
            "projects": projects,
            "weather": weather,
            "news": news_data,
        }

        event_bus.publish(Events.BRIEFING_READY, briefing_payload)
        return briefing_payload


# Global singleton
briefing_service = BriefingService()
