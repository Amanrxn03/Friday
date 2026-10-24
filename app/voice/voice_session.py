"""Voice Session Controller for Project FRIDAY.

Orchestrates the hands-free audio loop: wake word detection -> microphone speech capture ->
transcription -> task execution -> conversational vocal response.
"""

import threading
import logging
import time
from collections import deque
from typing import Optional, List
import numpy as np

from app.core.event_bus import event_bus, Events
from app.voice.audio_stream import audio_stream
from app.voice.wake_word import wake_word_detector
from app.voice.speech_to_text import stt_manager
from app.voice.text_to_speech import tts_manager
from app.voice.adaptive_vad import adaptive_vad
from app.core.metrics import latency_tracker, TurnLatencyRecord
from app.config import config

logger = logging.getLogger(__name__)


class VoiceSession:
    """Coordinates hands-free voice conversations and speech states."""

    def __init__(self):
        self.is_active = False
        self.is_listening_for_speech = False
        self._speech_buffer: List[np.ndarray] = []
        self._preroll_buffer: deque = deque(maxlen=8)  # Retain ~512ms pre-trigger audio
        self._lock = threading.RLock()
        self.current_turn_record: Optional[TurnLatencyRecord] = None

        # Subscribe to wake word events
        event_bus.subscribe(Events.WAKE_WORD_DETECTED, self._on_wake_word_triggered)

    def start(self) -> bool:
        """Start background audio capture and wake-word detector."""
        success = audio_stream.start()
        if success:
            audio_stream.add_listener(self._maintain_preroll)
            wake_word_detector.start()
            self.is_active = True
            logger.info("Voice session active and awaiting wake word: '%s'", config.voice.wake_word)
        return success

    def stop(self) -> None:
        """Stop all voice components."""
        wake_word_detector.stop()
        audio_stream.remove_listener(self._maintain_preroll)
        audio_stream.remove_listener(self._collect_speech_frames)
        audio_stream.stop()
        tts_manager.stop_speaking()
        self.is_active = False

    def push_to_talk(self) -> None:
        """User pressed push-to-talk shortcut or button."""
        wake_word_detector.trigger_manually(source="push_to_talk")

    def _maintain_preroll(self, chunk: np.ndarray) -> None:
        """Continuously keep the most recent ~500ms of audio frames to prevent clipping the wake word."""
        if not self.is_listening_for_speech:
            self._preroll_buffer.append(chunk)

    def _on_wake_word_triggered(self, data) -> None:
        """Called when wake phrase is detected or push-to-talk is clicked."""
        logger.info("Wake word detected! Entering active listening mode.")
        event_bus.publish(Events.VOICE_STATE, "LISTENING")

        # Initialize latency tracking
        import uuid
        self.current_turn_record = TurnLatencyRecord(turn_id=str(uuid.uuid4())[:8])
        self.current_turn_record.mark_wake_word()

        # Reset adaptive VAD
        adaptive_vad.reset()

        with self._lock:
            self.is_listening_for_speech = True
            self._speech_buffer = list(self._preroll_buffer)
            self._preroll_buffer.clear()
            audio_stream.add_listener(self._collect_speech_frames)

    def _collect_speech_frames(self, chunk: np.ndarray) -> None:
        """Buffer incoming microphone speech until adaptive pause/silence is detected."""
        with self._lock:
            if not self.is_listening_for_speech:
                return

            self._speech_buffer.append(chunk)
            vad_state = adaptive_vad.process_chunk(chunk)

            # End of speech detected by adaptive silence (150-200ms pause) or inactivity
            if vad_state in ("SPEECH_END", "INACTIVITY_TIMEOUT"):
                if self.current_turn_record:
                    self.current_turn_record.mark_vad_end_of_speech()
                self._finalize_speech_input()
                return

            # Fast conversational safety ceiling: ~3.2 seconds max (50 chunks @ 64ms)
            if len(self._speech_buffer) >= 50:
                self._finalize_speech_input()

    def _finalize_speech_input(self) -> None:
        """Stop buffering speech and submit for transcription."""
        with self._lock:
            if not self.is_listening_for_speech:
                return
            self.is_listening_for_speech = False
            audio_stream.remove_listener(self._collect_speech_frames)
            frames = list(self._speech_buffer)
            self._speech_buffer.clear()

        if not frames:
            return

        combined_audio = np.concatenate(frames)

        # Trim leading and trailing silence to minimize audio payload size and transcription latency
        try:
            abs_audio = np.abs(combined_audio)
            speech_pts = np.where(abs_audio > 0.008)[0]
            if len(speech_pts) > 0:
                pre_pad = int(16000 * 0.12)   # 120ms pre-roll
                post_pad = int(16000 * 0.12)  # 120ms post-roll
                start_pt = max(0, speech_pts[0] - pre_pad)
                end_pt = min(len(combined_audio), speech_pts[-1] + post_pad)
                combined_audio = combined_audio[start_pt:end_pt]
        except Exception:
            pass

        event_bus.publish(Events.VOICE_STATE, "PROCESSING")

        # Transcribe in background thread
        threading.Thread(
            target=self._transcribe_and_dispatch,
            args=(combined_audio, self.current_turn_record),
            daemon=True,
            name="SpeechTranscribeWorker",
        ).start()

    def _transcribe_and_dispatch(self, audio_data: np.ndarray, turn_record: Optional[TurnLatencyRecord]) -> None:
        """Transcribe speech and publish user message to conversation."""
        try:
            transcription = stt_manager.transcribe_audio(audio_data)
            if turn_record:
                turn_record.mark_stt_finalized()

            # Normalize wake phrase, typos, and acoustic homophones (e.g. 'hey pretty' -> 'hey kriti')
            from app.nlp.hinglish_normalizer import hinglish_normalizer
            norm_transcription = hinglish_normalizer.normalize_wake_phrase(transcription) if transcription else ""

            if norm_transcription and norm_transcription.strip():
                logger.info("Transcribed voice command: '%s' (raw: '%s')", norm_transcription, transcription)
                event_bus.publish(Events.USER_MESSAGE, {
                    "text": norm_transcription,
                    "source": "voice",
                    "latency_record": turn_record,
                })
            else:
                # If audio was captured immediately following wake word trigger, but STT returned empty
                # (e.g. short acoustic burst of 'Hey Kriti' or network hiccup)
                audio_dur = len(audio_data) / 16000.0 if audio_data is not None else 0.0
                if 0.3 <= audio_dur <= 2.5:
                    logger.info("Short audio burst (%.2fs) captured; defaulting to wake greeting.", audio_dur)
                    event_bus.publish(Events.USER_MESSAGE, {
                        "text": "Hey Kriti",
                        "source": "voice",
                        "latency_record": turn_record,
                    })
                else:
                    logger.info("No audible speech detected in buffer (duration: %.2fs).", audio_dur)
                    event_bus.publish(Events.VOICE_STATE, "IDLE")
        except Exception as e:
            logger.error("Error transcribing speech: %s", e)
            event_bus.publish(Events.VOICE_STATE, "IDLE")


# Global singleton
voice_session = VoiceSession()
