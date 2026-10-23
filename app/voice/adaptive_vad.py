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
    """Detects speech onset and end-of-utterance silence boundaries."""

    def __init__(
        self,
        energy_threshold: float = 0.015,
        silence_timeout_ms: int = 250,
        sample_rate: int = 16000,
    ):
        self.energy_threshold = energy_threshold
        self.silence_timeout_ms = silence_timeout_ms
        self.sample_rate = sample_rate

        self.is_speaking = False
        self._speech_start_time = 0.0
        self._last_speech_time = 0.0
        self._silence_start_time: Optional[float] = None

    def reset(self) -> None:
        self.is_speaking = False
        self._speech_start_time = 0.0
        self._last_speech_time = 0.0
        self._silence_start_time = None

    def process_chunk(self, chunk: np.ndarray) -> str:
        """Process an audio frame.

        Returns:
            'SILENCE': background noise
            'SPEECH_START': user just started speaking
            'SPEECH_CONTINUING': active speech frame
            'SPEECH_END': clear pause detected after speech (turn ready to finalize)
        """
        energy = float(np.sqrt(np.mean(chunk**2)))
        now = time.perf_counter()

        if energy >= self.energy_threshold:
            self._last_speech_time = now
            self._silence_start_time = None

            if not self.is_speaking:
                self.is_speaking = True
                self._speech_start_time = now
                logger.debug("VAD: Speech onset detected (RMS: %0.4f)", energy)
                return "SPEECH_START"
            return "SPEECH_CONTINUING"
        else:
            if self.is_speaking:
                if self._silence_start_time is None:
                    self._silence_start_time = now

                elapsed_silence_ms = (now - self._silence_start_time) * 1000.0
                if elapsed_silence_ms >= self.silence_timeout_ms:
                    self.is_speaking = False
                    self._silence_start_time = None
                    logger.debug("VAD: Speech end detected after %0.1f ms silence", elapsed_silence_ms)
                    return "SPEECH_END"
                return "SPEECH_CONTINUING"
            return "SILENCE"


# Global singleton
adaptive_vad = AdaptiveVAD()
