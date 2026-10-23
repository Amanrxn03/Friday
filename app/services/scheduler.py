"""Persistent Background Scheduler for Project FRIDAY.

Manages timed tasks, recurring daily morning briefings, and quiet hours enforcement.
"""

import threading
import time
import logging
from datetime import datetime
from typing import Callable, List, Dict, Any, Optional

from app.config import config
from app.services.briefing_service import briefing_service
from app.core.event_bus import event_bus, Events

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Runs scheduled background checks and recurring workflows."""

    def __init__(self, interval_seconds: int = 60):
        self.interval_seconds = interval_seconds
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_briefing_date: Optional[str] = None

    def start(self) -> None:
        """Start the background scheduler thread."""
        if self.is_running:
            return
        self.is_running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="FridayScheduler")
        self._thread.start()
        logger.info("Task Scheduler started (polling every %ds)", self.interval_seconds)

    def stop(self) -> None:
        """Stop the background scheduler."""
        self.is_running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("Task Scheduler stopped.")

    def is_in_quiet_hours(self) -> bool:
        """Check whether current local time falls within configured quiet hours."""
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")
        start = config.briefing.quiet_hours_start
        end = config.briefing.quiet_hours_end

        if start > end:  # Spans midnight (e.g. 22:00 to 07:00)
            return current_time_str >= start or current_time_str < end
        return start <= current_time_str < end

    def _run_loop(self) -> None:
        """Scheduler evaluation loop."""
        while not self._stop_event.is_set():
            try:
                self._check_scheduled_tasks()
            except Exception as e:
                logger.error("Error in scheduler tick: %s", e)
            self._stop_event.wait(self.interval_seconds)

    def _check_scheduled_tasks(self) -> None:
        """Inspect if it is time to deliver the morning briefing."""
        now = datetime.now()
        today_date = now.strftime("%Y-%m-%d")
        current_hm = now.strftime("%H:%M")

        # Check if morning briefing is due today and quiet hours are inactive
        if (
            config.briefing.enabled
            and current_hm >= config.briefing.briefing_time
            and self._last_briefing_date != today_date
            and not self.is_in_quiet_hours()
        ):
            self._last_briefing_date = today_date
            logger.info("Delivering scheduled morning briefing for %s", today_date)
            briefing_service.generate_morning_briefing()


# Global singleton
scheduler = TaskScheduler()
