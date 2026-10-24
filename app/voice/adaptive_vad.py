"""Adaptive Voice Activity Detection (VAD) for Project FRIDAY.

Detects conversational speech onset and fast end-of-speech pauses (150-300ms target)
to minimize turnaround latency without truncating sentences.
"""

import time
import logging
from typing import Optional, Callable
import numpy as np

from app.config import config

logger = logging.getLogger(__name__)


class AdaptiveVAD:
    """Detects speech onset and end-of-utterance silence boundaries with dynamic noise floor tracking."""

    def __init__(
        self,
        energy_threshold: float = 0.015,
        silence_timeout_ms: int = 200,
        sample_rate: int = 16000,
    ):
        self.base_energy_threshold = energy_threshold
        self.silence_timeout_ms = silence_timeout_ms
        self.sample_rate = sample_rate

        self.is_speaking = False
        self._speech_start_time = 0.0
        self._last_speech_time = 0.0
        self._silence_start_time: Optional[float] = None
        self._listen_start_time = 0.0
        self.noise_floor = 0.008

    def reset(self) -> None:
        self.is_speaking = False
        self._speech_start_time = 0.0
        self._last_speech_time = 0.0
        self._silence_start_time = None
        self._listen_start_time = time.perf_counter()

    def process_chunk(self, chunk: np.ndarray) -> str:
        """Process an audio frame with dynamic ambient noise floor and fast cutoff.

        Returns:
            'SILENCE': background noise
            'SPEECH_START': user just started speaking
            'SPEECH_CONTINUING': active speech frame
            'SPEECH_END': clear pause detected after speech (turn ready to finalize)
            'INACTIVITY_TIMEOUT': no speech detected after listening window
        """
        energy = float(np.sqrt(np.mean(chunk**2)))
        now = time.perf_counter()

        # Dynamic threshold adapts to room ambient noise level
        active_threshold = max(self.base_energy_threshold, self.noise_floor * 1.6)

        if energy >= active_threshold:
            self._last_speech_time = now
            self._silence_start_time = None

            if not self.is_speaking:
                self.is_speaking = True
                self._speech_start_time = now
                logger.debug("VAD: Speech onset detected (RMS: %0.4f, threshold: %0.4f)", energy, active_threshold)
                return "SPEECH_START"
            return "SPEECH_CONTINUING"
        else:
            # Update ambient noise floor estimate when not speaking
            if not self.is_speaking:
                self.noise_floor = 0.92 * self.noise_floor + 0.08 * energy
                # Inactivity safety: if no speech within 2.5s of activation, finalize
                if self._listen_start_time > 0 and (now - self._listen_start_time) > 2.5:
                    return "INACTIVITY_TIMEOUT"
                return "SILENCE"

            # If speaking, check silence duration
            if self._silence_start_time is None:
                self._silence_start_time = now

            elapsed_silence_ms = (now - self._silence_start_time) * 1000.0
            if elapsed_silence_ms >= self.silence_timeout_ms:
                self.is_speaking = False
                self._silence_start_time = None
                logger.debug("VAD: Fast speech end detected after %0.1f ms silence", elapsed_silence_ms)
                return "SPEECH_END"
            return "SPEECH_CONTINUING"


# Global singleton
adaptive_vad = AdaptiveVAD()
