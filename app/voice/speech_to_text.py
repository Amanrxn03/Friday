"""Speech-to-Text Transcription for Project FRIDAY.

Provides pluggable transcription backends including OpenAI Whisper API, local Windows speech,
and fallback text input.
"""

from abc import ABC, abstractmethod
import io
import wave
import logging
from typing import Optional
import numpy as np
import requests

from app.security.secret_store import secret_store
from app.config import config

logger = logging.getLogger(__name__)


class BaseSTTProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        pass


class OpenAIWhisperSTT(BaseSTTProvider):
    """Cloud transcription using OpenAI Whisper API."""

    API_URL = "https://api.openai.com/v1/audio/transcriptions"

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        api_key = secret_store.get_credential("openai")
        if not api_key:
            raise ValueError("OpenAI API key not configured for Whisper STT.")

        # Convert float32 numpy array to 16-bit PCM WAV in memory
        int16_data = (np.clip(audio_data, -1.0, 1.0) * 32767).astype(np.int16)
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(int16_data.tobytes())

        buffer.seek(0)
        files = {
            "file": ("audio.wav", buffer, "audio/wav"),
            "model": (None, "whisper-1"),
            "language": (None, "en"),
        }
        headers = {"Authorization": f"Bearer {api_key}"}

        resp = requests.post(self.API_URL, headers=headers, files=files, timeout=15)
        if resp.status_code == 200:
            return resp.json().get("text", "").strip()
        else:
            raise RuntimeError(f"Whisper API error: {resp.status_code} {resp.text}")


class FreeSpeechRecognitionSTT(BaseSTTProvider):
    """Free speech recognition requiring no API keys."""

    def __init__(self):
        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
        except ImportError:
            self.recognizer = None

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        if not self.recognizer or audio_data is None or len(audio_data) == 0:
            return ""

        try:
            import speech_recognition as sr
            int16_data = (np.clip(audio_data, -1.0, 1.0) * 32767).astype(np.int16)
            audio = sr.AudioData(int16_data.tobytes(), sample_rate, 2)
            
            # 1. Try Indian English first (critical for Indian accents and names like Kriti and Aman)
            text = None
            try:
                text = self.recognizer.recognize_google(audio, language="en-IN")
            except Exception:
                text = None

            # 2. Fall back to standard English
            if not text:
                try:
                    text = self.recognizer.recognize_google(audio, language="en-US")
                except Exception:
                    text = None

            # 3. Fall back to Hindi
            if not text:
                try:
                    text = self.recognizer.recognize_google(audio, language="hi-IN")
                except Exception:
                    text = None

            return text.strip() if text else ""
        except Exception as e:
            logger.debug("Free speech recognition result: %s", e)
            return ""


class FallbackSTT(BaseSTTProvider):
    """Safe fallback for offline, testing, or text-only scenarios."""

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        return ""


class SpeechToTextManager:
    """Manages active transcription provider with fallbacks."""

    def __init__(self):
        self.whisper = OpenAIWhisperSTT()
        self.free_stt = FreeSpeechRecognitionSTT()
        self.fallback = FallbackSTT()

    def transcribe_audio(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        if secret_store.has_credential("openai"):
            try:
                res = self.whisper.transcribe(audio_data, sample_rate)
                if res:
                    return res
            except Exception as e:
                logger.warning("Whisper STT failed, falling back: %s", e)

        # Free Speech Recognition (no API key needed)
        try:
            res = self.free_stt.transcribe(audio_data, sample_rate)
            if res:
                return res
        except Exception as e:
            logger.debug("Free STT error: %s", e)

        return self.fallback.transcribe(audio_data, sample_rate)


# Global STT manager singleton
stt_manager = SpeechToTextManager()
