# PROJECT FRIDAY — PERSONAL DESKTOP AI ASSISTANT

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11%20(64--bit)-00E5FF)](https://microsoft.com/windows)
[![Python](https://img.shields.io/badge/Python-3.11%20|%203.12%20|%203.13-blue)](https://python.org)
[![GUI](https://img.shields.io/badge/GUI-PySide6%20Qt-brightgreen)](https://qt.io)
[![Multilingual](https://img.shields.io/badge/Languages-EN%20%7C%20HI%20%7C%20Hinglish-cyan)](https://github.com)
[![Latency](https://img.shields.io/badge/Fast--Path-<5ms%20Bypass-success)](https://github.com)
[![Tests](https://img.shields.io/badge/Tests-21%2F21%20Passing-brightgreen)](https://pytest.org)

**FRIDAY** is an intelligent, witty, proactive, multilingual voice-enabled AI desktop companion built specifically for Windows 10/11. Inspired by futuristic AI assistants, she features three-language conversational understanding (English, Hindi, and natural Hinglish code-switching), sub-5ms deterministic fast-path intent execution, sentence-streaming neural TTS, adaptive voice activity detection (150-300ms pause), a hybrid AI routing engine, safe desktop automation, local wake-word detection, and source-backed daily briefings.

---

## 1. System Telemetry & Hardware Environment

FRIDAY automatically diagnoses and tailors her behavior to your detected hardware:
- **Operating System:** Windows 11 Home (64-bit, Build 10.0.26300)
- **Processor:** Intel(R) Core(TM) Ultra 9 185H (16 physical cores, 22 logical threads)
- **System Memory:** 32 GB RAM (High-throughput parallel processing)
- **Graphics & AI Acceleration:** NVIDIA GeForce RTX 4070 Laptop GPU (8,188 MiB VRAM, CUDA 13.4 ready)
- **Audio Subsystems:** Realtek High Definition Audio, NVIDIA Broadcast, Intel Smart Sound
- **Storage:** High-capacity SSD storage (C: / E:)

---

## 2. Core Architecture & Features

```
FRIDAY/
├── app/
│   ├── main.py                     # Primary Qt application entry point
│   ├── config.py                   # Centralized dataclass configurations & defaults
│   ├── core/
│   │   ├── event_bus.py            # Thread-safe pub/sub event bus
│   │   ├── permissions.py          # 3-Mode Autonomy Guard & Emergency Stop
│   │   ├── tool_registry.py        # Typed tool registry & OpenAI function schemas
│   │   ├── execution_manager.py    # Sandboxed execution with audit logs & verification
│   │   ├── task_planner.py         # Multi-step goal decomposition & system persona
│   │   └── orchestrator.py         # Conversation turns, tool calling, and speech dispatch
│   ├── ai/
│   │   ├── base_provider.py        # Abstract AI contract (generate, stream, tools)
│   │   ├── provider_manager.py     # Hybrid routing, VRAM-tailored model recs, fallbacks
│   │   ├── local_provider.py       # Ollama private local inference
│   │   ├── openai_provider.py      # OpenAI GPT-4o / GPT-4o-mini
│   │   ├── gemini_provider.py      # Google Gemini 2.0 Flash / Pro
│   │   └── anthropic_provider.py   # Anthropic Claude 3.5 Sonnet
│   ├── voice/
│   │   ├── audio_stream.py         # Real-time microphone capture & RMS energy
│   │   ├── wake_word.py            # Local "Hey Friday" wake phrase detector
│   │   ├── speech_to_text.py       # Pluggable Whisper STT + fallback
│   │   ├── text_to_speech.py       # Windows SAPI5 (pyttsx3) female voice + interruption
│   │   └── voice_session.py        # Hands-free conversational loop
│   ├── desktop/
│   │   ├── windows_controller.py   # Window focus, listing, volume, workstation lock
│   │   ├── application_launcher.py # Allowlisted app launching (VS Code, Explorer, etc.)
│   │   ├── file_manager.py         # Safe file operations with automatic undo backups
│   │   └── browser_automation.py   # Web searches, default browser launch, Playwright
│   ├── memory/
│   │   ├── database.py             # SQLite WAL-mode relational database
│   │   ├── task_repository.py      # Checkpointed task & subtask persistence
│   │   └── memory_service.py       # Verified facts vs inferred preferences, privacy mode
│   ├── services/
│   │   ├── news_service.py         # RSS-backed news (India, World, Tech, Science) & weather
│   │   ├── briefing_service.py     # Synthesized morning briefing & spoken greetings
│   │   ├── startup_service.py      # Windows HKCU Run registry integration
│   │   └── scheduler.py            # Background timer for briefings & quiet hours
│   ├── ui/
│   │   ├── theme.py                # Futuristic dark charcoal (#0B0E14) & cyan stylesheet
│   │   ├── main_window.py          # Master dashboard, header, sidebar, stacked views
│   │   ├── conversation.py         # Modern chat bubbles with tool execution cards
│   │   ├── dashboard.py            # Real-time CPU, RAM, Disk, Battery telemetry
│   │   ├── tasks_view.py           # Persistent task management & step checkpoints
│   │   ├── memory_view.py          # Declarative memory table, JSON export & clear
│   │   ├── settings.py             # AI credentials, autonomy mode, voice sliders
│   │   ├── compact_hud.py          # Always-on-top floating minimalist HUD
│   │   └── widgets/
│   │       ├── waveform.py         # QPainter-rendered animated voice visualizer
│   │       └── approval_dialog.py  # High-impact security confirmation modal
│   └── security/
│       ├── secret_store.py         # Windows Credential Manager keyring adapter
│       ├── audit_log.py            # Rotating audit log with automatic secret redaction
│       └── path_policy.py          # Strict path traversal & directory containment guard
├── tests/                          # 15 automated pytest suites covering all subsystems
├── run_friday.bat                  # One-click desktop launcher (no terminal needed)
├── install_friday.bat              # One-click installation & dependency setup wizard
├── requirements.txt                # Production Python dependencies
└── .env.example                    # Configuration template with placeholders
```

---

## 3. Quick Start & Launch Instructions

### Method A: One-Click Windows Launch (Recommended)
You do not need to keep the IDE open or execute terminal commands every day:
1. Double-click `run_friday.bat` in the project root.
2. FRIDAY launches in native windowed mode with full background services.

### Method B: Manual Command Line
```powershell
# Navigate to the workspace
cd c:\Friday

# Run tests
.venv\Scripts\pytest.exe -v tests

# Launch application
.venv\Scripts\python.exe app\main.py
```

---

## 4. Multi-AI Hybrid Router Configuration

FRIDAY includes a unified provider adapter for local and cloud models:

| Provider | Type | Recommended Models | Configuration |
|---|---|---|---|
| **Ollama** | Local (Private, 0 Cost) | `llama3.2:3b`, `qwen2.5-coder:7b` | Runs automatically on `http://localhost:11434` |
| **OpenAI** | Cloud (High Reasoning) | `gpt-4o-mini`, `gpt-4o` | Settings UI -> OpenAI API Key |
| **Google Gemini** | Cloud (Fast & Capable) | `gemini-2.0-flash`, `gemini-1.5-pro` | Settings UI -> Gemini API Key |
| **Anthropic** | Cloud (Code & Nuance) | `claude-3-5-sonnet-20241022` | Settings UI -> Anthropic Key |

### Local Model Recommendation for RTX 4070 (8 GB VRAM)
Because your system features an NVIDIA GeForce RTX 4070 Laptop GPU with 8 GB VRAM, FRIDAY recommends:
```bash
ollama run qwen2.5-coder:7b
# or
ollama run llama3.2:3b
```
Both models fit comfortably inside your 8 GB VRAM budget with full GPU acceleration and zero CPU offloading overhead.

### Security of Credentials
- API keys are **never stored in plaintext** in source files or logs.
- Credentials are saved in the encrypted **Windows Credential Manager** (`keyring` backend) under service target `ProjectFRIDAY`.
- All logs run through `redact_sensitive_data()`, which scrubs keys matching `sk-...`, `sk-ant-...`, `AIza...`, and Bearer tokens.

---

## 5. Safe Autonomy & Permission Modes

FRIDAY operates under 3 configurable autonomy modes:

1. **MODE 1 — SUGGEST:**
   FRIDAY analyzes tasks, prepares plans, and asks for user approval before executing any tool.
2. **MODE 2 — APPROVED AUTONOMY (Default):**
   FRIDAY autonomously executes low-risk, reversible actions within authorized workspaces (reading files, listing directories, checking battery, focusing windows, searching notes). Any consequential operation pauses and triggers the **Approval Modal**.
3. **MODE 3 — CONFIRM HIGH-IMPACT ACTIONS:**
   Requires explicit confirmation before:
   - Deleting files or clearing folders.
   - Overwriting existing files (FRIDAY creates an automated timestamped backup in `data/backups/` first).
   - Executing system commands or locking the workstation.
   - External communication or posting.

### Global Emergency Stop
Click the red **🛑 EMERGENCY STOP** button in the header (or trigger via keyboard / voice) to:
- Immediately halt any active or queued desktop automation.
- Cancel pending approvals.
- Block any new tool calls until explicitly reset.

---

## 6. Voice, Wake Word & Speech Synthesis

- **Wake Word:** Configured to **"Hey Friday"**. Also supports **Push-To-Talk** via the `🎙️ Push to Talk` button.
- **Waveform Visualizer:** Animated cyan bar visualizer responds in real time to your voice's RMS energy and FRIDAY's speech state.
- **Natural Voice:** Powered by Windows SAPI5 with female voice selection (`Microsoft Zira`) and adjustable speaking rate and volume in Settings.
- **Instant Speech Interruption:** Press `⏹️ Stop Voice` or trigger the wake word while she is speaking to immediately halt audio playback.
- **Mute Control:** Toggle `🎤 Mute` anytime to disconnect the microphone stream.

---

---

## 7. Multilingual Engine (English, Hindi, Hinglish)

FRIDAY natively supports three primary language modes with zero translation delays:
1. **English:** Natural Indian English pronunciation and phrasing.
2. **Hindi:** Devanagari script understanding and formal/conversational Hindi responses.
3. **Hinglish:** Natural Roman-script Hindi-English code-switching without requiring manual user translation.

### Code-Switching & Technical Token Preservation
- **Technical Integrity:** Tokens like `VS Code`, `python`, `git`, `notepad`, `main.py`, `pytest` are strictly preserved and never transliterated or mistranslated.
- **Colloquial Variants:** Seamlessly understands interchangeable actions:
  - `"notepad kholo"` / `"नोटपैड खोलो"` / `"open notepad"` -> `launch_application(notepad)`
  - `"screen lock karo"` / `"स्क्रीन लॉक करो"` / `"lock pc"` -> `lock_workstation()`
  - `"volume 70 pe set karo"` / `"वॉल्यूम 70 करो"` / `"set volume to 70"` -> `adjust_system_volume(70)`
  - `"ruk jao"` / `"रुकिए"` / `"stop"` / `"cancel"` -> Instant Emergency Stop & Speech Cancellation

---

## 8. Ultra-Low-Latency Architecture & Telemetry

FRIDAY measures every segment of the conversation turn:
`Microphone -> Wake Word -> Adaptive VAD -> STT -> Intent Understanding -> LLM Reasoning -> Tool Execution -> TTS -> Playback`

- **Deterministic Fast-Path Intent Matching:** Bypasses slow cloud/LLM network calls for predictable commands in **< 5 ms** (benchmarked at ~0.05 ms).
- **Adaptive VAD End-of-Speech Detection:** Re-calibrated pause threshold (150–300 ms) to detect when the user has finished speaking without cutting off natural pauses.
- **Sentence-Streaming TTS:** Begins audio playback on the first completed speakable clause instead of waiting for the full response.
- **Barge-In Interruption:** Cancels active speech and pending tasks the instant user speaks a cancellation phrase (`"stop"`, `"ruk jao"`).
- **Live Latency Tracker:** Sliding-window analytics compute **p50 (median)** and **p95** end-to-end response times visible on the Dashboard.

---

## 9. Multilingual & Latency Automated Benchmarks

Execute the automated benchmark across English, Hindi, and Hinglish:
```powershell
.venv\Scripts\python.exe app\main.py --benchmark
```

### Benchmark Results
```text
======================================================================
 PROJECT FRIDAY — MULTILINGUAL LATENCY & ACCURACY BENCHMARK
======================================================================
Evaluating 11 Multilingual Commands across EN, HI, and Hinglish...
Input Command                  | Lang     | Latency   | Status
----------------------------------------------------------------------
open notepad                   | en       |   1.69 ms | PASS (Deterministic <5ms)
adjust volume to 50            | en       |   0.03 ms | PASS (Deterministic <5ms)
system status                  | en       |   0.01 ms | PASS (Deterministic <5ms)
stop                           | en       |   0.01 ms | PASS (Deterministic <5ms)
कैलकुलेटर खोलो                 | hi       |   0.10 ms | PASS (Deterministic <5ms)
सिस्टम स्टेटस                  | hi       |   0.01 ms | PASS (Deterministic <5ms)
रुक जाओ                        | hi       |   0.01 ms | PASS (Deterministic <5ms)
notepad kholo                  | hinglish |   0.02 ms | PASS (Deterministic <5ms)
volume 65 pe set karo          | hinglish |   0.02 ms | PASS (Deterministic <5ms)
screen lock karo               | hinglish |   0.01 ms | PASS (Deterministic <5ms)
ruk jao                        | hinglish |   0.01 ms | PASS (Deterministic <5ms)
----------------------------------------------------------------------
Total Commands Tested:      11
Command Intent Accuracy:    100.0%
Deterministic Latency p50:  0.01 ms (Target: <5.0 ms)
Deterministic Latency p95:  0.90 ms
======================================================================
```

---

## 10. Automated Test Suite

Project FRIDAY includes 21 comprehensive automated unit and smoke tests (`pytest`):
- `tests/test_foundation.py`: Config defaults, credential redaction, path traversal guards, SQLite WAL schemas, verified vs inferred memory, emergency stop.
- `tests/test_ai_and_planner.py`: ProviderManager routing, offline fallback, VRAM-tailored model logic, task decomposition.
- `tests/test_desktop_and_tools.py`: Tool registry schemas, safe file writes with undo backups, execution manager autonomy approvals.
- `tests/test_services_and_ui.py`: News and weather fetcher, morning briefing synthesis, Windows startup service, PySide6 UI component smoke tests.
- `tests/test_multilingual_and_latency.py`: Three-language detection (EN, HI, Hinglish), technical token preservation, deterministic intent matching (<5ms), negative commands & cancellation, fast-path latency benchmarks, and p50/p95 latency tracker.

```powershell
.venv\Scripts\pytest.exe -v tests
# Result: 21 passed in ~14s
```

---

## 11. Windows Startup Integration

To launch FRIDAY automatically whenever you sign in to your PC:
1. Open FRIDAY -> Click **⚙️ Settings & Security**.
2. Check the box: **"Launch FRIDAY automatically when signing in to Windows"**.
3. FRIDAY registers `run_friday.bat` into `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`.
4. No administrator privileges are required, and you can disable it with a single click anytime.
