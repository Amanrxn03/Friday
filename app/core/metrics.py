"""High-Resolution Latency & Telemetry Tracker for Project FRIDAY.

Measures each segment of the conversational loop:
Microphone -> Wake Word -> VAD -> STT -> Intent Understanding -> Model Reasoning ->
Tool Execution -> Speech Synthesis -> Audio Playback.
Maintains rolling window analytics to compute median (p50) and p95 latency.
"""

import time
import math
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class TurnLatencyRecord:
    turn_id: str
    language: str = "en"
    intent_type: str = "general"
    fast_path_used: bool = False

    # Timestamps (perf_counter in fractional seconds)
    start_time: float = field(default_factory=time.perf_counter)
    wake_word_time: Optional[float] = None
    vad_end_of_speech_time: Optional[float] = None
    stt_finalized_time: Optional[float] = None
    first_model_token_time: Optional[float] = None
    first_audio_chunk_time: Optional[float] = None
    tool_completion_time: Optional[float] = None
    end_time: Optional[float] = None

    def mark_wake_word(self) -> None:
        self.wake_word_time = time.perf_counter()

    def mark_vad_end_of_speech(self) -> None:
        self.vad_end_of_speech_time = time.perf_counter()

    def mark_stt_finalized(self) -> None:
        self.stt_finalized_time = time.perf_counter()

    def mark_first_model_token(self) -> None:
        self.first_model_token_time = time.perf_counter()

    def mark_first_audio_chunk(self) -> None:
        self.first_audio_chunk_time = time.perf_counter()

    def mark_tool_completion(self) -> None:
        self.tool_completion_time = time.perf_counter()

    def finalize(self) -> Dict[str, float]:
        if self.end_time is None:
            self.end_time = time.perf_counter()
        return self.get_durations_ms()

    def get_durations_ms(self) -> Dict[str, float]:
        """Compute millisecond durations for each milestone."""
        ref = self.start_time
        res: Dict[str, float] = {}

        if self.vad_end_of_speech_time:
            res["vad_eos_latency_ms"] = round((self.vad_end_of_speech_time - ref) * 1000, 2)
            base = self.vad_end_of_speech_time
        else:
            base = ref

        if self.stt_finalized_time:
            res["stt_latency_ms"] = round((self.stt_finalized_time - base) * 1000, 2)

        if self.first_model_token_time:
            token_base = self.stt_finalized_time or base
            res["time_to_first_token_ms"] = round((self.first_model_token_time - token_base) * 1000, 2)

        if self.first_audio_chunk_time:
            audio_base = self.vad_end_of_speech_time or base
            res["time_to_first_audio_ms"] = round((self.first_audio_chunk_time - audio_base) * 1000, 2)

        if self.tool_completion_time:
            res["tool_exec_ms"] = round((self.tool_completion_time - base) * 1000, 2)

        total_end = self.end_time if self.end_time is not None else time.perf_counter()
        res["total_e2e_ms"] = round((total_end - ref) * 1000, 2)
        return res


class LatencyTracker:
    """Maintains sliding metrics history and computes percentiles."""

    def __init__(self, history_limit: int = 100):
        self.history_limit = history_limit
        self.history: deque = deque(maxlen=history_limit)

    def record_turn(self, record: TurnLatencyRecord) -> Dict[str, float]:
        metrics = record.finalize()
        self.history.append({
            "turn_id": record.turn_id,
            "language": record.language,
            "intent_type": record.intent_type,
            "fast_path": record.fast_path_used,
            "metrics": metrics,
        })
        logger.info(
            "Turn %s [%s] E2E Latency: %0.2f ms (Fast-Path: %s)",
            record.turn_id, record.language, metrics.get("total_e2e_ms", 0), record.fast_path_used
        )
        return metrics

    def get_summary_stats(self) -> Dict[str, Any]:
        """Compute p50 (median) and p95 across recorded turns."""
        if not self.history:
            return {
                "count": 0,
                "e2e_p50_ms": 0.0,
                "e2e_p95_ms": 0.0,
                "fast_path_ratio": 0.0,
            }

        e2e_values = [h["metrics"].get("total_e2e_ms", 0) for h in self.history if "total_e2e_ms" in h["metrics"]]
        e2e_values.sort()

        fast_path_count = sum(1 for h in self.history if h["fast_path"])

        def percentile(data: List[float], p: float) -> float:
            if not data:
                return 0.0
            k = (len(data) - 1) * p
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return data[int(k)]
            d0 = data[int(f)] * (c - k)
            d1 = data[int(c)] * (k - f)
            return round(d0 + d1, 2)

        return {
            "count": len(self.history),
            "e2e_p50_ms": percentile(e2e_values, 0.50),
            "e2e_p95_ms": percentile(e2e_values, 0.95),
            "fast_path_ratio": round(fast_path_count / len(self.history), 2),
            "latest": self.history[-1] if self.history else None,
        }


# Global latency tracker singleton
latency_tracker = LatencyTracker()
