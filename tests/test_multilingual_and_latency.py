"""Unit and Benchmark Tests for Multilingual Voice, Intent Matching, and Ultra-Low Latency."""

import time
import pytest

from app.nlp.language_detector import LanguageDetector
from app.nlp.hinglish_normalizer import HinglishNormalizer
from app.nlp.intent_matcher import IntentMatcher, ParsedIntent
from app.core.metrics import LatencyTracker, TurnLatencyRecord
from app.core.orchestrator import Orchestrator
from app.core.permissions import permissions_engine


def test_three_language_detection():
    """Ensure accurate automatic detection of English, Devanagari Hindi, and Roman Hinglish."""
    detector = LanguageDetector()

    # English
    assert detector.detect("Friday, open my project folder and summarize files.") == "en"
    assert detector.detect("What is the current CPU utilization?") == "en"

    # Hindi (Devanagari)
    assert detector.detect("फ्राइडे, मेरा प्रोजेक्ट फोल्डर खोलो और मुझे बताओ।") == "hi"
    assert detector.detect("सिस्टम का स्टेटस क्या है?") == "hi"

    # Hinglish (Roman script code-switching)
    assert detector.detect("Friday, mera project folder open karo aur batao kal maine kaunsi files pe kaam kiya tha.") == "hinglish"
    assert detector.detect("VS Code kholo aur python script run kar do.") == "hinglish"
    assert detector.detect("Awaaz thodi kam karo please.") == "hinglish"


def test_hinglish_technical_token_preservation():
    """Ensure technical keywords, application names, and filenames are preserved without distortion."""
    normalizer = HinglishNormalizer()

    # Application target identification
    assert normalizer.extract_app_target("Notepad open kar do") == "notepad"
    assert normalizer.extract_app_target("VS Code kholo please") == "vscode"
    assert normalizer.extract_app_target("Calculator chalao") == "calculator"
    assert normalizer.extract_app_target("File Explorer dikhao") == "explorer"

    # Semantic action extraction
    assert normalizer.extract_action("VS Code kholo") == "OPEN"
    assert normalizer.extract_action("App band kar do") == "CLOSE"
    assert normalizer.extract_action("Ruk jao") == "CANCEL"
    assert normalizer.extract_action("Mat karo") == "CANCEL"


def test_fast_deterministic_intent_matching():
    """Ensure predictable commands in English, Hindi, and Hinglish match with high confidence (<5ms)."""
    matcher = IntentMatcher()

    # 1. English Launch
    res_en = matcher.match_intent("open notepad")
    assert res_en is not None
    assert res_en.tool_name == "launch_application"
    assert res_en.tool_args == {"app_alias": "notepad"}

    # 2. Hinglish Launch
    res_hinglish = matcher.match_intent("notepad kholo")
    assert res_hinglish is not None
    assert res_hinglish.tool_name == "launch_application"
    assert res_hinglish.tool_args == {"app_alias": "notepad"}
    assert res_hinglish.detected_language == "hinglish"
    assert "Notepad open kar rahi hoon" in res_hinglish.conversational_replies["hinglish"]

    # 3. Hindi Launch
    res_hi = matcher.match_intent("कैलकुलेटर खोलो")
    assert res_hi is not None
    assert res_hi.tool_name == "launch_application"
    assert res_hi.tool_args == {"app_alias": "calculator"}

    # 4. Volume in Hinglish
    res_vol = matcher.match_intent("volume 65 pe set karo")
    assert res_vol is not None
    assert res_vol.tool_name == "adjust_system_volume"
    assert res_vol.tool_args == {"level_percent": 65}

    # 5. Lock PC
    res_lock = matcher.match_intent("screen lock karo")
    assert res_lock is not None
    assert res_lock.tool_name == "lock_workstation"

    # 6. Status in Hinglish
    res_status = matcher.match_intent("battery kitni hai")
    assert res_status is not None
    assert res_status.tool_name == "get_system_status"


def test_negative_commands_and_cancellation():
    """Ensure stop, cancel, and negative commands are immediately recognized as cancellations."""
    matcher = IntentMatcher()

    commands = [
        "stop",
        "cancel",
        "ruk jao",
        "mat karo",
        "don't do that",
        "रुक जाओ",
        "chup ho jao",
    ]

    for cmd in commands:
        intent = matcher.match_intent(cmd)
        assert intent is not None, f"Failed to match cancellation command: '{cmd}'"
        assert intent.is_cancellation is True
        assert intent.tool_name == "emergency_stop"


def test_fast_path_latency_benchmark():
    """Benchmark deterministic fast-path execution to ensure sub-5ms processing."""
    matcher = IntentMatcher()
    t0 = time.perf_counter()
    parsed = matcher.match_intent("notepad kholo")
    match_ms = (time.perf_counter() - t0) * 1000.0
    assert parsed is not None
    # Assert deterministic intent matching takes under 5ms
    assert match_ms < 5.0

    orch = Orchestrator()
    permissions_engine.reset_emergency_stop()

    # Fast cancellation execution takes under 25ms (instant bypass)
    t1 = time.perf_counter()
    outcome_cancel = orch.process_user_turn("ruko", source="text")
    cancel_ms = (time.perf_counter() - t1) * 1000.0
    assert outcome_cancel.get("fast_path") is True
    assert cancel_ms < 25.0

    # Ensure app launching routes through fast-path
    permissions_engine.reset_emergency_stop()
    outcome = orch.process_user_turn("notepad kholo", source="text")
    assert outcome.get("fast_path") is True
    assert "Notepad" in outcome.get("reply")


def test_latency_tracker_percentiles():
    """Ensure LatencyTracker computes p50 and p95 across recorded turns accurately."""
    tracker = LatencyTracker(history_limit=10)

    # Record 5 mock turns with varying latency
    latencies = [10.0, 20.0, 30.0, 40.0, 100.0]
    for idx, lat in enumerate(latencies):
        rec = TurnLatencyRecord(turn_id=f"t_{idx}")
        rec.start_time = 0.0
        rec.end_time = lat / 1000.0
        tracker.record_turn(rec)

    stats = tracker.get_summary_stats()
    assert stats["count"] == 5
    assert stats["e2e_p50_ms"] == 30.0
    assert stats["e2e_p95_ms"] >= 80.0


def test_followup_question_after_instructions():
    """Verify FRIDAY concludes instruction completions with 'What else can I do for you?'."""
    orch = Orchestrator()
    permissions_engine.reset_emergency_stop()

    # English command
    res_en = orch.process_user_turn("open notepad", source="text")
    assert "What else can I do for you?" in res_en.get("reply")

    # Hinglish command
    res_hing = orch.process_user_turn("notepad kholo", source="text")
    assert "What else can I do for you?" in res_hing.get("reply")

    # Hindi command
    res_hi = orch.process_user_turn("कैलकुलेटर खोलो", source="text")
    assert "मैं आपके लिए और क्या कर सकती हूँ?" in res_hi.get("reply")

    # Cancellation should not append the follow-up
    res_cancel = orch.process_user_turn("stop", source="text")
    assert "What else can I do for you?" not in res_cancel.get("reply")


def test_conversational_prefix_and_low_latency_matching():
    """Verify natural conversational prefixes and wake words are stripped for <1ms fast path."""
    matcher = IntentMatcher()

    test_queries = [
        ("Hey Friday, open youtube", "open_website"),
        ("Friday can you open notepad", "launch_application"),
        ("Suno Friday, volume 70 pe set karo", "adjust_system_volume"),
        ("Friday what time is it", "get_current_time"),
        ("Please lock my screen", "lock_workstation"),
        ("Who are you", "get_system_status"),
        ("Hello Friday", "get_system_status"),
    ]

    for query, expected_tool in test_queries:
        t0 = time.perf_counter()
        intent = matcher.match_intent(query)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        assert intent is not None, f"Failed to match query: '{query}'"
        assert intent.tool_name == expected_tool, f"Expected {expected_tool}, got {intent.tool_name} for '{query}'"
        assert elapsed_ms < 5.0, f"Latency {elapsed_ms:.2f}ms exceeded 5.0ms target"


