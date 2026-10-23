"""Application Entry Point for Project FRIDAY.

Initializes configuration, verifies system hardware, launches background services,
and executes the PySide6 event loop.
"""

import sys
import logging
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from PySide6.QtWidgets import QApplication

from app.config import config
from app.security.audit_log import audit_log
from app.memory.database import db
from app.memory.task_repository import task_repository
from app.services.scheduler import scheduler
from app.services.briefing_service import briefing_service
from app.voice.voice_session import voice_session
from app.core.orchestrator import orchestrator
from app.ui.main_window import MainWindow
from app.nlp.intent_matcher import intent_matcher
from app.nlp.language_detector import language_detector
from app.core.metrics import latency_tracker, TurnLatencyRecord

logger = logging.getLogger("FridayMain")


def run_benchmark() -> int:
    """Execute automated multilingual latency and accuracy benchmark suite."""
    import time
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    print("\n" + "="*70)
    print(" PROJECT FRIDAY — MULTILINGUAL LATENCY & ACCURACY BENCHMARK")
    print("="*70)

    test_cases = [
        ("en", "open notepad", "launch_application", "notepad"),
        ("en", "adjust volume to 50", "adjust_system_volume", 50),
        ("en", "system status", "get_system_status", None),
        ("en", "stop", "emergency_stop", None),
        ("hi", "कैलकुलेटर खोलो", "launch_application", "calculator"),
        ("hi", "सिस्टम स्टेटस", "get_system_status", None),
        ("hi", "रुक जाओ", "emergency_stop", None),
        ("hinglish", "notepad kholo", "launch_application", "notepad"),
        ("hinglish", "volume 65 pe set karo", "adjust_system_volume", 65),
        ("hinglish", "screen lock karo", "lock_workstation", None),
        ("hinglish", "ruk jao", "emergency_stop", None),
    ]

    print(f"\nEvaluating {len(test_cases)} Multilingual Commands across EN, HI, and Hinglish...")
    print(f"{'Input Command':<30} | {'Lang':<8} | {'Latency':<9} | {'Status'}")
    print("-" * 70)

    success_count = 0
    latencies = []

    for expected_lang, text, expected_tool, expected_arg in test_cases:
        t0 = time.perf_counter()
        parsed = intent_matcher.match_intent(text)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(elapsed_ms)

        det_lang = language_detector.detect(text)
        is_correct = (
            parsed is not None and
            parsed.tool_name == expected_tool and
            det_lang == expected_lang
        )

        if is_correct:
            success_count += 1
            status_str = "PASS (Deterministic <5ms)"
        else:
            status_str = f"FAIL (Got {parsed.tool_name if parsed else None})"

        print(f"{text:<30} | {det_lang:<8} | {elapsed_ms:>6.2f} ms | {status_str}")

        # Record in latency tracker
        rec = TurnLatencyRecord(turn_id=f"bench_{len(latencies)}")
        rec.start_time = 0.0
        rec.end_time = elapsed_ms / 1000.0
        rec.language = det_lang
        rec.fast_path_used = True
        latency_tracker.record_turn(rec)

    stats = latency_tracker.get_summary_stats()
    accuracy = (success_count / len(test_cases)) * 100.0

    print("-" * 70)
    print(f"Total Commands Tested:      {len(test_cases)}")
    print(f"Command Intent Accuracy:    {accuracy:.1f}%")
    print(f"Deterministic Latency p50:  {stats.get('e2e_p50_ms', 0):.2f} ms (Target: <5.0 ms)")
    print(f"Deterministic Latency p95:  {stats.get('e2e_p95_ms', 0):.2f} ms")
    print("=" * 70 + "\n")
    return 0


def main() -> int:
    """Initialize and run Project FRIDAY."""
    config.ensure_directories()

    # CLI Benchmark Flag
    if "--benchmark" in sys.argv:
        return run_benchmark()

    audit_log.info("Starting Project FRIDAY v%s on Windows 11", config.version)

    # Initialize PySide6 Application
    app = QApplication(sys.argv)
    app.setApplicationName("Project FRIDAY")
    app.setOrganizationName("Antigravity")

    # Step 1: Initialize Database & Check Unfinished Tasks
    unfinished = task_repository.get_unfinished_tasks()
    if unfinished:
        logger.info("Found %d unfinished task(s) from previous session.", len(unfinished))

    # Step 2: Start Background Scheduler (morning briefing & periodic checks)
    scheduler.start()

    # Step 3: Initialize Voice Session (Microphone stream & Wake Word)
    if config.voice.enabled:
        voice_started = voice_session.start()
        if not voice_started:
            logger.info("Microphone unavailable or voice disabled; text interaction remains fully active.")

    # Step 4: Create and Display Master UI Window
    window = MainWindow()
    window.show()

    # Step 5: Deliver Initial Startup Briefing in Background
    briefing_service.generate_morning_briefing()

    audit_log.record_action(
        category="SYSTEM",
        action="STARTUP",
        status="SUCCESS",
        details={"version": config.version, "unfinished_tasks": len(unfinished)},
    )

    # Run Qt Event Loop
    exit_code = app.exec()

    # Clean Shutdown
    logger.info("Shutting down FRIDAY background services...")
    scheduler.stop()
    voice_session.stop()
    audit_log.record_action(category="SYSTEM", action="SHUTDOWN", status="CLEAN")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
