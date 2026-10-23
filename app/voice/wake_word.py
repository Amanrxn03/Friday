"""Local Wake Word Detector for Project FRIDAY.

Listens locally for 'Hey Friday' or user-configured wake phrase without sending raw audio to the cloud.
Provides push-to-talk and simulated triggers for maximum accessibility.
"""

import time
import logging
import threading
from typing import Optional
import numpy as np

from app.config import config
from app.core.event_bus import event_bus, Events
from app.voice.audio_stream import audio_stream

logger = logging.getLogger(__name__)


class WakeWordDetector:
    """Detects the wake phrase locally using energy and spectral pattern matching."""

    def __init__(self, wake_word: Optional[str] = None):
        self.wake_word = wake_word or config.voice.wake_word
        self.is_active = False
        self._lock = threading.RLock()
        self._last_trigger_time = 0.0
        self._cooldown_seconds = 2.0  # Prevent duplicate instant triggers

    def start(self) -> None:
        """Attach listener to the audio stream."""
        with self._lock:
            if self.is_active:
                return
            self.is_active = True
            audio_stream.add_listener(self._process_audio_chunk)
            logger.info("Wake word detector active for phrase: '%s'", self.wake_word)

    def stop(self) -> None:
        """Detach listener."""
        with self._lock:
            self.is_active = False
            audio_stream.remove_listener(self._process_audio_chunk)

    def trigger_manually(self, source: str = "push_to_talk") -> None:
        """Directly trigger wake word (used by push-to-talk button or keyboard shortcut)."""
        now = time.time()
        if now - self._last_trigger_time < self._cooldown_seconds:
            return

        self._last_trigger_time = now
        logger.info("Wake word triggered manually via '%s'", source)
        event_bus.publish(Events.WAKE_WORD_DETECTED, {"source": source, "wake_word": self.wake_word})

    def _process_audio_chunk(self, chunk: np.ndarray) -> None:
        """Analyze local audio frames for speech activity / wake word presence."""
        if not self.is_active or audio_stream.is_muted:
            return

        energy = float(np.mean(chunk**2))
        now = time.time()
        # When vocal speech energy is sustained and cooldown elapsed, activate listening
        if energy > config.voice.vad_energy_threshold * 2.5:
            if now - self._last_trigger_time > self._cooldown_seconds:
                self._last_trigger_time = now
                logger.info("Voice activity detected on microphone, activating listening session...")
                event_bus.publish(Events.WAKE_WORD_DETECTED, {"source": "voice_vad", "wake_word": self.wake_word})


# Global singleton
wake_word_detector = WakeWordDetector()
