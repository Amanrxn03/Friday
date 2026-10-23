"""Audio Input Stream and Voice Activity Detection for Project FRIDAY.

Captures microphone audio via sounddevice, calculates RMS energy for the UI visualizer,
handles mute toggles, and buffers speech frames for processing.
"""

import threading
import logging
import time
from typing import Optional, Callable, List
import numpy as np

try:
    import sounddevice as sd
    SD_AVAILABLE = True
except Exception:
    SD_AVAILABLE = False

from app.config import config
from app.core.event_bus import event_bus, Events

logger = logging.getLogger(__name__)


class AudioStream:
    """Manages microphone input capture, audio levels, and mute states."""

    def __init__(self):
        self.sample_rate = config.voice.input_sample_rate
        self.channels = 1
        self.block_size = 1024
        self.is_muted = False
        self.is_recording = False
        self._stream = None
        self._lock = threading.RLock()
        self.last_audio_level = 0.0
        self.audio_listeners: List[Callable[[np.ndarray], None]] = []

    def start(self) -> bool:
        """Start listening to the system default microphone."""
        if not config.voice.enabled:
            logger.info("Voice is disabled in configuration.")
            return False

        if not SD_AVAILABLE:
            logger.warning("sounddevice is not available. Audio input disabled.")
            return False

        with self._lock:
            if self.is_recording:
                return True

            try:
                self._stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    blocksize=self.block_size,
                    callback=self._audio_callback,
                    dtype="float32",
                )
                self._stream.start()
                self.is_recording = True
                logger.info("Audio stream successfully initialized at %d Hz", self.sample_rate)
                return True
            except Exception as e:
                logger.warning("Could not start microphone stream (will fall back to text): %s", e)
                self.is_recording = False
                return False

    def stop(self) -> None:
        """Stop microphone capture."""
        with self._lock:
            if self._stream:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None
            self.is_recording = False
            self.last_audio_level = 0.0
            event_bus.publish(Events.AUDIO_LEVEL, 0.0)

    def set_muted(self, muted: bool) -> None:
        """Toggle microphone mute."""
        with self._lock:
            self.is_muted = muted
            level = 0.0 if muted else self.last_audio_level
            event_bus.publish(Events.VOICE_STATE, "MUTED" if muted else "LISTENING")
            event_bus.publish(Events.AUDIO_LEVEL, level)
            logger.info("Microphone mute set to: %s", muted)

    def toggle_mute(self) -> bool:
        """Toggle current mute state and return new state."""
        self.set_muted(not self.is_muted)
        return self.is_muted

    def add_listener(self, listener: Callable[[np.ndarray], None]) -> None:
        """Register a callback for raw audio data."""
        with self._lock:
            if listener not in self.audio_listeners:
                self.audio_listeners.append(listener)

    def remove_listener(self, listener: Callable[[np.ndarray], None]) -> None:
        with self._lock:
            if listener in self.audio_listeners:
                self.audio_listeners.remove(listener)

    def _audio_callback(self, indata, frames, time_info, status) -> None:
        """sounddevice real-time audio callback."""
        if self.is_muted:
            self.last_audio_level = 0.0
            event_bus.publish(Events.AUDIO_LEVEL, 0.0)
            return

        # Compute RMS energy
        rms = float(np.sqrt(np.mean(indata**2)))
        normalized = min(1.0, rms * 15.0)  # scale for visualizer display
        self.last_audio_level = normalized

        # Emit audio level for waveform widget
        event_bus.publish(Events.AUDIO_LEVEL, normalized)

        # Dispatch audio frames to listeners
        with self._lock:
            listeners = list(self.audio_listeners)
        for listener in listeners:
            try:
                listener(indata.copy())
            except Exception as e:
                logger.error("Audio listener error: %s", e)


# Global audio stream singleton
audio_stream = AudioStream()
