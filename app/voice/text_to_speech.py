"""Text-to-Speech Engine for Project FRIDAY.

Provides multilingual speech synthesis featuring Windows SAPI5 (pyttsx3) for 100% offline
conversational speech with a warm, natural feminine voice, sentence streaming for ultra-low latency,
and instant interruption support.
"""

import threading
import logging
import queue
import re
from typing import Optional, Generator, Any
import pyttsx3

from app.config import config
from app.core.event_bus import event_bus, Events
from app.security.secret_store import secret_store

logger = logging.getLogger(__name__)


class TextToSpeechManager:
    """Manages multilingual text-to-speech synthesis with pre-warmed persistent engine."""

    def __init__(self):
        self.speech_rate = max(200, config.voice.speech_rate)
        self.volume = config.voice.volume
        self.is_speaking = False
        self._lock = threading.RLock()
        self._speech_queue: queue.Queue = queue.Queue()
        self._stop_requested = threading.Event()
        self._engine = None
        self._cached_voices: dict = {}
        self._worker_thread: Optional[threading.Thread] = None

        # Pre-warm persistent engine on startup
        self._start_worker()

    def _start_worker(self) -> None:
        """Start persistent worker thread maintaining the COM SAPI5 engine."""
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="FridayTTSPersistentWorker",
        )
        self._worker_thread.start()

    def _worker_loop(self) -> None:
        """Dedicated persistent loop preventing repeated COM SAPI5 initialization overhead."""
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except Exception:
            pass

        try:
            self._engine = pyttsx3.init("sapi5")
            self._engine.setProperty("rate", self.speech_rate)
            self._engine.setProperty("volume", self.volume)

            voices = self._engine.getProperty("voices")
            for v in voices:
                vname = v.name.lower()
                if "hindi" in vname or "kalpana" in vname or "hemant" in vname:
                    self._cached_voices["hi"] = v.id
                if "india" in vname or "heera" in vname or "zira" in vname or "female" in vname:
                    if "en" not in self._cached_voices:
                        self._cached_voices["en"] = v.id
            logger.info("Persistent SAPI5 TTS engine pre-warmed successfully.")
        except Exception as e:
            logger.warning("Could not pre-warm SAPI5 engine: %s", e)
            self._engine = None

        while True:
            item = self._speech_queue.get()
            if item is None:
                break

            chunk_text, lang = item
            if self._stop_requested.is_set():
                self._speech_queue.task_done()
                continue

            with self._lock:
                self.is_speaking = True
            event_bus.publish(Events.VOICE_STATE, "SPEAKING")

            try:
                target_voice = self._cached_voices.get(lang) or self._cached_voices.get("en")
                if self._engine:
                    if target_voice:
                        try:
                            self._engine.setProperty("voice", target_voice)
                        except Exception:
                            pass
                    self._engine.setProperty("rate", self.speech_rate)
                    self._engine.setProperty("volume", self.volume)
                    self._engine.say(chunk_text)
                    self._engine.runAndWait()
            except Exception as e:
                logger.debug("TTS playback chunk error: %s", e)
            finally:
                with self._lock:
                    self.is_speaking = False
                event_bus.publish(Events.VOICE_STATE, "IDLE")
                self._speech_queue.task_done()

    def speak(self, text: str, language: str = "en", interrupt_existing: bool = True) -> None:
        """Speak the provided text with instant clause streaming and zero COM init latency."""
        if not text or not text.strip() or not config.voice.enabled:
            return

        clean_text = text.strip()

        if interrupt_existing:
            self.stop_speaking()

        self._stop_requested.clear()

        # Split into sentence clauses so speech output begins immediately on first clause
        clauses = [c.strip() for c in re.split(r"(?<=[.!?\n।])\s+", clean_text) if c.strip()]
        if not clauses:
            clauses = [clean_text]

        for clause in clauses:
            self._speech_queue.put((clause, language))

    def speak_stream(self, token_generator: Generator[str, None, Any], language: str = "en") -> None:
        """Stream speech synthesis on sentence boundaries for ultra-low latency response."""
        self.stop_speaking()
        self._stop_requested.clear()

        sentence_end_pattern = re.compile(r"([.!?\n।|])\s*")

        def stream_worker():
            buffer = ""
            for token in token_generator:
                if self._stop_requested.is_set():
                    break
                buffer += token
                matches = list(sentence_end_pattern.finditer(buffer))
                if matches:
                    last_match = matches[-1]
                    end_pos = last_match.end()
                    chunk = buffer[:end_pos].strip()
                    buffer = buffer[end_pos:]
                    if chunk and not self._stop_requested.is_set():
                        self._speech_queue.put((chunk, language))

            if buffer.strip() and not self._stop_requested.is_set():
                self._speech_queue.put((buffer.strip(), language))

        threading.Thread(target=stream_worker, daemon=True, name="FridayTTSStreamWorker").start()

    def stop_speaking(self) -> None:
        """Immediately interrupt and silence ongoing speech."""
        self._stop_requested.set()
        # Drain queued items
        while not self._speech_queue.empty():
            try:
                self._speech_queue.get_nowait()
                self._speech_queue.task_done()
            except Exception:
                break

        if self._engine:
            try:
                self._engine.stop()
            except Exception:
                pass

        with self._lock:
            if not self.is_speaking:
                return
            self.is_speaking = False

        logger.info("FRIDAY Speech interrupted by user.")
        event_bus.publish(Events.SPEECH_INTERRUPTED)
        event_bus.publish(Events.VOICE_STATE, "IDLE")

    def update_settings(self, rate: Optional[int] = None, volume: Optional[float] = None) -> None:
        """Update voice rate and volume."""
        if rate is not None:
            self.speech_rate = rate
        if volume is not None:
            self.volume = max(0.0, min(1.0, volume))


# Global TTS manager singleton
tts_manager = TextToSpeechManager()
