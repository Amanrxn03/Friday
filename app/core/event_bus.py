"""Thread-Safe Event Bus for Project FRIDAY.

Enables asynchronous, decoupled communication across GUI, AI providers, voice pipeline,
task planner, desktop automation, and security subsystems.
"""

import threading
import logging
from typing import Callable, Dict, List, Any
from enum import Enum

logger = logging.getLogger(__name__)


class Events(str, Enum):
    # Assistant Lifecycle & State
    STATE_CHANGED = "state.changed"             # Initializing, Listening, Thinking, Executing, Speaking, Error
    EMERGENCY_STOP = "emergency.stop"           # Immediate halt triggered
    EMERGENCY_RESET = "emergency.reset"         # System resumed

    # Conversation & AI
    USER_MESSAGE = "conversation.user_message"
    ASSISTANT_CHUNK = "conversation.assistant_chunk"
    ASSISTANT_MESSAGE = "conversation.assistant_message"
    PROVIDER_CHANGED = "ai.provider_changed"

    # Voice Pipeline
    VOICE_STATE = "voice.state"                 # IDLE, LISTENING, PROCESSING, SPEAKING, MUTED
    AUDIO_LEVEL = "voice.audio_level"           # Waveform amplitude (0.0 to 1.0)
    WAKE_WORD_DETECTED = "voice.wake_word"
    SPEECH_INTERRUPTED = "voice.interrupted"

    # Tool Execution & Approvals
    TOOL_START = "tool.start"
    TOOL_COMPLETE = "tool.complete"
    TOOL_ERROR = "tool.error"
    APPROVAL_REQUIRED = "approval.required"
    APPROVAL_RESOLVED = "approval.resolved"

    # Tasks & Briefings
    TASK_UPDATED = "task.updated"
    BRIEFING_READY = "briefing.ready"
    SYSTEM_NOTIFICATION = "system.notification"


class EventBus:
    """Centralized thread-safe publish-subscribe dispatcher."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Any], None]]] = {}
        self._lock = threading.RLock()

    def subscribe(self, event_type: str, callback: Callable[[Any], None]) -> None:
        """Register a subscriber callback for an event type."""
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            if callback not in self._subscribers[event_type]:
                self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable[[Any], None]) -> None:
        """Remove a subscriber callback."""
        with self._lock:
            if event_type in self._subscribers and callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)

    def publish(self, event_type: str, data: Any = None) -> None:
        """Publish an event to all registered subscribers."""
        with self._lock:
            callbacks = list(self._subscribers.get(event_type, []))

        for cb in callbacks:
            try:
                cb(data)
            except Exception as e:
                logger.error("Error executing subscriber for '%s': %s", event_type, e, exc_info=True)

    def clear(self) -> None:
        """Clear all registered subscriptions (useful for unit testing)."""
        with self._lock:
            self._subscribers.clear()


# Global event bus singleton
event_bus = EventBus()
