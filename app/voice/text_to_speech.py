"""Text-to-Speech Engine for Project FRIDAY.

Provides multilingual speech synthesis featuring custom voice cloning (Kriti's Voice),
cloud neural synthesis (ElevenLabs Instant Voice Cloning), Windows SAPI5 / OneCore
persistent worker engine for 100% offline conversational speech, and instant interruption support.
"""

import threading
import logging
import queue
import re
import os
import winsound
from pathlib import Path
from typing import Optional, Generator, Any, List, Dict
import pyttsx3
import requests

from app.config import config
from app.core.event_bus import event_bus, Events
from app.security.secret_store import secret_store

logger = logging.getLogger(__name__)


class TextToSpeechManager:
    """Manages multilingual text-to-speech synthesis with pre-warmed persistent engine and voice cloning."""

    def __init__(self):
        self.speech_rate = max(185, config.voice.speech_rate)
        self.volume = config.voice.volume
        self.voice_profile = config.voice.voice_profile or "kriti"
        self.custom_voice_path = config.voice.custom_voice_path
        self.custom_voice_name = config.voice.custom_voice_name
        self.is_speaking = False
        self.last_speech_end_time: float = 0.0
        self._lock = threading.RLock()
        self._speech_queue: queue.Queue = queue.Queue()
        self._stop_requested = threading.Event()
        self._engine = None
        self._cached_voices: Dict[str, str] = {}
        self._system_voices: Dict[str, str] = {}
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
                if "heera" in vname:
                    self._system_voices["heera"] = v.id
                elif "zira" in vname:
                    self._system_voices["zira"] = v.id
                elif "david" in vname:
                    self._system_voices["david"] = v.id
                elif "ravi" in vname:
                    self._system_voices["ravi"] = v.id
                elif "kalpana" in vname:
                    self._system_voices["kalpana"] = v.id

                if "hindi" in vname or "kalpana" in vname or "hemant" in vname:
                    self._cached_voices["hi"] = v.id
                if "india" in vname or "heera" in vname or "zira" in vname or "female" in vname:
                    if "en" not in self._cached_voices:
                        self._cached_voices["en"] = v.id

            logger.info("Persistent SAPI5 TTS engine pre-warmed successfully. Installed voices: %s", list(self._system_voices.keys()))
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
                # 1. Attempt ElevenLabs Voice Clone if profile is kriti and key is available
                if self.voice_profile == "kriti" and self._has_elevenlabs_key():
                    played_clone = self._synthesize_elevenlabs(chunk_text)
                    if played_clone:
                        continue

                # 2. Local SAPI5 synthesis with selected voice profile
                target_voice = self._resolve_voice_id(lang)
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
                    import time
                    self.last_speech_end_time = time.time()
                event_bus.publish(Events.VOICE_STATE, "IDLE")
                self._speech_queue.task_done()

    def _resolve_voice_id(self, lang: str = "en") -> Optional[str]:
        """Resolve COM voice ID based on active voice profile and language."""
        if self.voice_profile == "kriti":
            # For Kriti local fallback, prefer Indian English natural feminine voice (Heera / Kalpana)
            return (
                self._system_voices.get("heera")
                or self._cached_voices.get("hi")
                or self._cached_voices.get("en")
            )
        elif self.voice_profile in self._system_voices:
            return self._system_voices[self.voice_profile]
        return self._cached_voices.get(lang) or self._cached_voices.get("en")

    def _has_elevenlabs_key(self) -> bool:
        """Check if an ElevenLabs API key is available."""
        return bool(secret_store.get_credential("elevenlabs") or os.getenv("ELEVENLABS_API_KEY"))

    def _synthesize_elevenlabs(self, text: str) -> bool:
        """Synthesize speech using ElevenLabs voice cloning API with Kriti's voice sample."""
        try:
            api_key = secret_store.get_credential("elevenlabs") or os.getenv("ELEVENLABS_API_KEY")
            voice_id = config.voice.elevenlabs_voice_id

            # If voice_id not configured yet, attempt auto-clone from kriti.wav
            if not voice_id and os.path.exists(self.custom_voice_path):
                clone_res = self.clone_voice_elevenlabs(api_key=api_key, sample_path=self.custom_voice_path)
                voice_id = clone_res.get("voice_id")
                if voice_id:
                    config.voice.elevenlabs_voice_id = voice_id

            if not voice_id:
                return False

            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            headers = {
                "xi-api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            }
            payload = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.55,
                    "similarity_boost": 0.85,
                },
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            if resp.status_code == 200 and resp.content:
                # Save to temp wav/mp3 and play
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                    tmp.write(resp.content)
                    tmp_path = tmp.name

                self.play_audio_file(tmp_path)
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
                return True
        except Exception as e:
            logger.debug("ElevenLabs TTS error, falling back to local voice: %s", e)
        return False

    def clone_voice_elevenlabs(self, api_key: Optional[str] = None, sample_path: Optional[str] = None) -> Dict[str, Any]:
        """Clone Kriti's voice using ElevenLabs Instant Voice Cloning API."""
        key = api_key or secret_store.get_credential("elevenlabs") or os.getenv("ELEVENLABS_API_KEY")
        if not key:
            return {"success": False, "error": "ElevenLabs API key not configured"}

        audio_file = sample_path or self.custom_voice_path
        if not os.path.exists(audio_file):
            return {"success": False, "error": f"Voice sample file not found at {audio_file}"}

        try:
            url = "https://api.elevenlabs.io/v1/voices/add"
            headers = {"xi-api-key": key}
            data = {
                "name": "Kriti FRIDAY Voice",
                "description": "Voice clone of Kriti for Project FRIDAY assistant",
            }
            with open(audio_file, "rb") as f:
                files = {"files": (os.path.basename(audio_file), f, "audio/wav")}
                resp = requests.post(url, headers=headers, data=data, files=files, timeout=20)

            if resp.status_code == 200:
                v_id = resp.json().get("voice_id")
                config.voice.elevenlabs_voice_id = v_id
                return {"success": True, "voice_id": v_id}
            else:
                return {"success": False, "error": resp.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def play_audio_file(self, file_path: str) -> None:
        """Play any audio file (WAV) directly with instant zero-latency playback."""
        if not file_path or not os.path.exists(file_path):
            return

        with self._lock:
            self.is_speaking = True
        event_bus.publish(Events.VOICE_STATE, "SPEAKING")

        try:
            if file_path.lower().endswith(".wav"):
                winsound.PlaySound(file_path, winsound.SND_FILENAME)
            else:
                # Use PySide6 / QtMultimedia for MP3 / OGG files if needed
                from PySide6.QtCore import QUrl, QEventLoop
                from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
                from PySide6.QtWidgets import QApplication
                import sys

                _app = QApplication.instance() or QApplication(sys.argv)
                player = QMediaPlayer()
                audio_out = QAudioOutput()
                player.setAudioOutput(audio_out)
                audio_out.setVolume(self.volume)
                player.setSource(QUrl.fromLocalFile(os.path.abspath(file_path)))

                loop = QEventLoop()
                player.mediaStatusChanged.connect(
                    lambda status: loop.quit() if status == QMediaPlayer.MediaStatus.EndOfMedia else None
                )
                player.play()
                loop.exec()
        except Exception as e:
            logger.debug("Audio file playback error: %s", e)
        finally:
            with self._lock:
                self.is_speaking = False
                import time
                self.last_speech_end_time = time.time()
            event_bus.publish(Events.VOICE_STATE, "IDLE")

    def play_custom_sample(self, sample_path: Optional[str] = None) -> None:
        """Play Kriti's original voice sample on demand."""
        target = sample_path or self.custom_voice_path
        if not target or not os.path.exists(target):
            # Try finding the wav or ogg in assets
            for candidate in [
                r"c:\Friday\app\assets\custom_voices\kriti.wav",
                r"c:\Friday\app\assets\custom_voices\kriti.ogg",
                os.path.expanduser(r"~\Downloads\Whatsapp Downloads\Kriti's Voice.ogg"),
            ]:
                if os.path.exists(candidate):
                    target = candidate
                    break

        if target and os.path.exists(target):
            threading.Thread(target=self.play_audio_file, args=(target,), daemon=True, name="FridayCustomVoicePlayback").start()

    def list_available_voices(self) -> List[Dict[str, str]]:
        """Return available voices including custom clone and discovered system voices."""
        voices = [
            {
                "id": "kriti",
                "name": "🌟 Kriti's Voice (Custom Clone)",
                "description": "Selected custom voice cloned from Kriti's WhatsApp recording",
                "type": "custom",
            },
            {
                "id": "heera",
                "name": "Microsoft Heera (Indian English)",
                "description": "Natural Indian English feminine speech",
                "type": "system",
            },
            {
                "id": "zira",
                "name": "Microsoft Zira (US English)",
                "description": "Clear US English feminine speech",
                "type": "system",
            },
            {
                "id": "david",
                "name": "Microsoft David (US English)",
                "description": "US English masculine speech",
                "type": "system",
            },
        ]
        return voices

    def set_voice_profile(self, profile_id: str) -> None:
        """Set the active voice profile."""
        self.voice_profile = profile_id
        config.voice.voice_profile = profile_id
        logger.info("Active voice profile set to: %s", profile_id)

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
        # Immediately silence any winsound playback
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass

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

