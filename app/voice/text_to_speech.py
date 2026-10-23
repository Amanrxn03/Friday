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
    """Manages multilingual text-to-speech synthesis with sentence-chunked streaming playback."""

    def __init__(self):
        self.speech_rate = config.voice.speech_rate
        self.volume = config.voice.volume
        self.is_speaking = False
        self._lock = threading.RLock()
        self._speech_thread: Optional[threading.Thread] = None
        self._stop_requested = threading.Event()
        self._speech_queue: queue.Queue = queue.Queue()
        self._queue_worker_thread: Optional[threading.Thread] = None

    def _get_engine(self, language: str = "en"):
        """Initialize pyttsx3 COM engine configured for the requested language."""
        try:
            engine = pyttsx3.init("sapi5")
            engine.setProperty("rate", self.speech_rate)
            engine.setProperty("volume", self.volume)

            voices = engine.getProperty("voices")
            selected_voice_id = None

            # 1. If Hindi requested, search for Hindi voice
            if language == "hi":
                for voice in voices:
                    vname = voice.name.lower()
                    if "hindi" in vname or "kalpana" in vname or "hemant" in vname:
                        selected_voice_id = voice.id
                        break

            # 2. If not found or English/Hinglish, look for Indian English or natural feminine voice
            if not selected_voice_id:
                for voice in voices:
                    vname = voice.name.lower()
                    if "india" in vname or "heera" in vname or "zira" in vname or "hazel" in vname or "female" in vname:
                        selected_voice_id = voice.id
                        break

            if selected_voice_id:
                engine.setProperty("voice", selected_voice_id)

            return engine
        except Exception as e:
            logger.warning("Could not initialize SAPI5 speech engine: %s", e)
            return None

    def speak(self, text: str, language: str = "en", interrupt_existing: bool = True) -> None:
        """Speak the provided text in a background thread without blocking the GUI."""
        if not text or not text.strip() or not config.voice.enabled:
            return

        clean_text = text.strip()

        if interrupt_existing and self.is_speaking:
            self.stop_speaking()

        self._stop_requested.clear()
        self._speech_thread = threading.Thread(
            target=self._run_speech_worker,
            args=(clean_text, language),
            daemon=True,
            name="FridayTTSWorker",
        )
        self._speech_thread.start()

    def speak_stream(self, token_generator: Generator[str, None, Any], language: str = "en") -> None:
        """Stream speech synthesis on sentence boundaries for ultra-low latency response."""
        self.stop_speaking()
        self._stop_requested.clear()

        # Sentence delimiters: English (. ! ? \n) and Hindi Purna Viram (।)
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
                    if chunk:
                        self._speak_chunk_sync(chunk, language)

            # Flush remaining tokens
            if buffer.strip() and not self._stop_requested.is_set():
                self._speak_chunk_sync(buffer.strip(), language)

        threading.Thread(target=stream_worker, daemon=True, name="FridayTTSStreamWorker").start()

    def _speak_chunk_sync(self, text: str, language: str = "en") -> None:
        """Synchronously speak one sentence chunk on the worker thread."""
        if self._stop_requested.is_set() or not text:
            return

        with self._lock:
            self.is_speaking = True

        event_bus.publish(Events.VOICE_STATE, "SPEAKING")
        engine = self._get_engine(language=language)
        if engine:
            try:
                engine.say(text)
                engine.runAndWait()
            except Exception as e:
                logger.error("TTS chunk synthesis error: %s", e)
            finally:
                try:
                    engine.stop()
                except Exception:
                    pass

        with self._lock:
            self.is_speaking = False

        event_bus.publish(Events.VOICE_STATE, "IDLE")

    def _run_speech_worker(self, text: str, language: str = "en") -> None:
        """Background thread executing complete speech text."""
        with self._lock:
            self.is_speaking = True

        event_bus.publish(Events.VOICE_STATE, "SPEAKING")
        logger.info("FRIDAY Speaking (%s): '%s'", language, text[:60])

        engine = self._get_engine(language=language)
        if engine:
            try:
                engine.say(text)
                engine.runAndWait()
            except Exception as e:
                logger.error("TTS synthesis error: %s", e)
            finally:
                try:
                    engine.stop()
                except Exception:
                    pass

        with self._lock:
            self.is_speaking = False

        event_bus.publish(Events.VOICE_STATE, "IDLE")

    def stop_speaking(self) -> None:
        """Immediately interrupt and silence ongoing speech."""
        with self._lock:
            self._stop_requested.set()
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
