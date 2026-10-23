"""Voice and Speech Subsystem for Project FRIDAY."""

from app.voice.audio_stream import AudioStream, audio_stream
from app.voice.wake_word import WakeWordDetector, wake_word_detector
from app.voice.speech_to_text import SpeechToTextManager, stt_manager
from app.voice.text_to_speech import TextToSpeechManager, tts_manager
from app.voice.voice_session import VoiceSession, voice_session

__all__ = [
    "AudioStream",
    "audio_stream",
    "WakeWordDetector",
    "wake_word_detector",
    "SpeechToTextManager",
    "stt_manager",
    "TextToSpeechManager",
    "tts_manager",
    "VoiceSession",
    "voice_session",
]
