# 🎙️ PROJECT FRIDAY — Personal Desktop AI Assistant

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11%20(64--bit)-00E5FF?style=flat-square&logo=windows)](https://microsoft.com/windows)
[![Python](https://img.shields.io/badge/Python-3.11%20|%203.12%20|%203.13-3776AB?style=flat-square&logo=python)](https://python.org)
[![GUI](https://img.shields.io/badge/GUI-PySide6%20Qt%206-41CD52?style=flat-square&logo=qt)](https://qt.io)
[![Languages](https://img.shields.io/badge/Languages-English%20%7C%20Hindi%20%7C%20Hinglish-FF6F00?style=flat-square)](https://github.com/Amanrxn03/Friday)
[![AI Engine](https://img.shields.io/badge/Local%20AI-Ollama%20(Llama%203.2)-blueviolet?style=flat-square)](https://ollama.com)
[![Hardware Acceleration](https://img.shields.io/badge/GPU-NVIDIA%20RTX%20Accelerated-76B900?style=flat-square&logo=nvidia)](https://nvidia.com)
[![Tests](https://img.shields.io/badge/Tests-21%2F21%20Passing-brightgreen?style=flat-square)](https://pytest.org)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

> **FRIDAY** is a fast, voice-enabled, multilingual AI desktop companion built specifically for Windows 10/11. She understands natural **English**, **Hindi (Devanagari)**, and conversational **Hinglish (code-switching)**, speaks responses out loud, executes desktop actions with safety safeguards, and runs privately on your local NVIDIA GPU (or connects to cloud models).

---

## 📑 Table of Contents
1. [Key Highlights](#-key-highlights)
2. [Quick Start Guide](#-quick-start-guide)
3. [Voice & Speech Interaction](#-voice--speech-interaction)
4. [Multilingual Understanding (EN / HI / Hinglish)](#-multilingual-understanding-en--hi--hinglish)
5. [AI Provider Setup (Local GPU & Cloud)](#-ai-provider-setup-local-gpu--cloud)
6. [Desktop Automation & Available Tools](#-desktop-automation--available-tools)
7. [Safe Autonomy & Security Safeguards](#-safe-autonomy--security-safeguards)
8. [Performance & Latency Benchmarks](#-performance--latency-benchmarks)
9. [Project Architecture](#-project-architecture)
10. [Automated Test Suite](#-automated-test-suite)
11. [Troubleshooting & FAQ](#-troubleshooting--faq)

---

## ⚡ Key Highlights

* **Ultra-Low Latency (<5ms Intent Matching):** Routine commands like launching apps, adjusting volume, or locking the workstation execute in under 1 ms via a deterministic bypass.
* **Three-Language Support:** Speaks and understands English, Hindi, and natural Hinglish code-switching in the same sentence without requiring translation.
* **100% Private Local Inference:** Bundled with local Ollama support (`llama3.2:latest`) accelerated on your NVIDIA GeForce RTX GPU with 8 GB VRAM at $0 API cost.
* **Zero-Downtime Offline Fallback:** If network drops or models update, FRIDAY seamlessly switches to her built-in offline engine so she never stops responding.
* **Real Desktop Automation:** Reads and creates files with automatic undo backups, launches approved apps, manages active windows, and checks battery/hardware.
* **Safety First:** 3-tier autonomy guard with explicit confirmation modals before any destructive operation (file deletes, file overwrites, workstation locks).

---

## 🚀 Quick Start Guide

### Step 1: Initial Installation (First Time Only)
Open a terminal in the project directory and run the setup script:
```powershell
cd C:\Friday
.\install_friday.bat
```
This automatically creates the `.venv` virtual environment, upgrades `pip`, and installs all necessary dependencies.

### Step 2: Launch FRIDAY

#### Option A: One-Click Launch (Recommended)
Double-click **`run_friday.bat`** in File Explorer.

#### Option B: From Windows PowerShell
```powershell
cd C:\Friday; .\run_friday.bat
```

#### Option C: Direct Console Mode (Shows Real-Time Logs)
```powershell
cd C:\Friday; .\.venv\Scripts\python.exe app\main.py
```

---

## 🎙️ Voice & Speech Interaction

FRIDAY is built from the ground up for hands-free conversational desktop use:

| Feature | How It Works |
|---|---|
| **Voice Activation** | Simply speak into your microphone or say *"Hey Friday"*. Vocal energy triggers automatic speech capture. |
| **Push-to-Talk** | Click the **`🎙️ Push to Talk`** button in the header or HUD to speak on demand. |
| **Instant Interruption (Barge-In)** | Say *"stop"*, *"ruk jao"*, or click **`⏹️ Stop Voice`** to immediately halt speech and ongoing actions. |
| **Adaptive VAD** | Detects end-of-speech pauses (150–300 ms) so FRIDAY answers quickly without cutting off mid-sentence. |
| **Sentence-Streaming Speech** | Uses Windows SAPI5 (`pyttsx3`) with female voice selection (`Microsoft Zira` / `Microsoft Heera`) and starts playback on the very first completed clause. |
| **Mute Control** | Click **`🎤 Mute`** in the header to disconnect microphone streaming at any time. |

---

## 🌐 Multilingual Understanding (EN / HI / Hinglish)

FRIDAY treats **Hinglish** as a first-class language rather than simple translation. She preserves technical tokens (`VS Code`, `python`, `git`, `main.py`, file paths) without altering them.

### Examples of Equivalent Commands:

| Desired Action | English 🇬🇧 | Hindi (हिंदी) 🇮🇳 | Hinglish (Code-Switching) 🗣️ |
|---|---|---|---|
| **Launch Notepad** | *"Open Notepad"* | *"नोटपैड खोलो"* | *"Notepad kholo"* |
| **Adjust Volume** | *"Set volume to 70"* | *"वॉल्यूम 70 प्रतिशत सेट करो"* | *"Volume 70 pe set kar do"* |
| **System Telemetry** | *"Show system status"* | *"सिस्टम स्टेटस दिखाओ"* | *"System specs check karo"* |
| **Lock Workstation** | *"Lock my computer"* | *"कंप्यूटर लॉक करो"* | *"Screen lock karo"* |
| **Cancel / Stop** | *"Stop what you're doing"* | *"रुक जाओ"* | *"Ruk jao"* |
| **Morning Briefing** | *"Give me the morning briefing"* | *"आज की मुख्य खबरें बताओ"* | *"Aaj ka morning briefing batao"* |

---

## 🧠 AI Provider Setup (Local GPU & Cloud)

FRIDAY features a **Hybrid Multi-AI Routing Engine**:

```
                       User Request
                            │
               ┌────────────┴────────────┐
               ▼                         ▼
    Predictable Desktop Intent    Complex Reasoning / Q&A
               │                         │
     <5ms Deterministic Fast-Path         ▼
               │                ┌─────────────────┐
     Execute Action Directly    │ Provider Manager │
                                └────────┬────────┘
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
             Ollama (Local)       Cloud Providers     Offline Fallback
           llama3.2:latest        OpenAI / Gemini/    Built-in Desktop
           (GPU Accelerated)      Claude (Optional)        Engine
```

### 1. Local AI: Ollama (Default & Recommended)
FRIDAY uses **Ollama** running locally on your PC:
* **Default Model:** `llama3.2:latest` (2.0 GB instruction-tuned model).
* **Hardware Utilization:** Runs with full GPU acceleration on NVIDIA GeForce RTX GPUs (takes ~2.5 GB of your 8 GB VRAM).
* **Cost:** 100% Free, unlimited, private, and works completely offline.

To pull alternative local models tailored for 8 GB VRAM:
```powershell
ollama pull qwen2.5-coder:7b     # High-precision coding model
ollama pull llama3.2:3b          # Fast conversational model
```

### 2. Cloud Providers (Optional)
If you prefer using cloud frontier models:
1. Open FRIDAY -> Go to **⚙️ Settings & Security**.
2. Select your provider (**OpenAI**, **Gemini**, or **Anthropic**).
3. Paste your API key and click **Save**.
4. Keys are encrypted and stored in **Windows Credential Manager** (`keyring` backend) and never stored in plaintext.

---

## 🛠️ Desktop Automation & Available Tools

FRIDAY includes 15+ built-in desktop tools with strict permission checks:

* **System Controls:** `get_system_status`, `adjust_system_volume`, `lock_workstation`.
* **Window Management:** `list_open_windows`, `focus_window`.
* **Application Launcher:** `launch_application` (VS Code, Notepad, Calculator, Chrome, Edge, Terminal, File Explorer).
* **Safe File Operations:** `read_file`, `write_file`, `delete_file`, `list_directory`, `search_files`.
  * *Note:* Overwritten or deleted files create an automatic timestamped backup in `data/backups/`.
* **Web & News:** `open_website`, `search_web`, `get_briefing` (Weather via Open-Meteo & RSS news).
* **Declarative Memory:** `remember_fact`, `recall_fact`.

---

## 🛡️ Safe Autonomy & Security Safeguards

FRIDAY never executes dangerous actions behind your back:

### Three Autonomy Modes (Configurable in Settings):
1. **Mode 1 — SUGGEST:** Analyzes tasks, prepares plans, and asks for approval before calling any tool.
2. **Mode 2 — APPROVED AUTONOMY (Default):** Autonomously executes safe, reversible actions (reading files, listing folders, checking telemetry, focusing windows). Any destructive action pauses and opens an **Approval Modal**.
3. **Mode 3 — CONFIRM HIGH-IMPACT:** Requires explicit button click confirmation for file deletes, file overwrites, workstation locking, and external requests.

### 🛑 Global Emergency Stop
Click the red **EMERGENCY STOP** button in the header (or say *"Stop"* / *"Ruk jao"*) to immediately kill all queued automations and halt speech.

---

## 📊 Performance & Latency Benchmarks

FRIDAY tracks milestone latencies for every conversational turn:

| Milestone Metric | Engineering Target | Measured Result |
|---|---|---|
| **Deterministic Intent Matching** | < 5 ms | **0.01 – 1.69 ms** |
| **End-of-Speech Detection (VAD)** | 150 – 300 ms | **180 ms** |
| **First Audible Response (Fast-Path)** | < 800 ms | **~120 ms** |
| **Semantic Command Accuracy** | > 95% | **100% (11/11 Passed)** |
| **Median Latency (p50)** | < 5.0 ms (Fast-Path) | **0.01 ms** |
| **Tail Latency (p95)** | < 25.0 ms | **0.90 ms** |

Run the automated multilingual benchmark anytime:
```powershell
.venv\Scripts\python.exe app\main.py --benchmark
```

---

## 📁 Project Architecture

```
FRIDAY/
├── app/
│   ├── main.py                     # Application entry point & Qt event loop
│   ├── config.py                   # Centralized configuration dataclasses
│   ├── core/
│   │   ├── event_bus.py            # Thread-safe pub/sub event bus
│   │   ├── permissions.py          # 3-Mode Autonomy engine & Emergency Stop
│   │   ├── tool_registry.py        # 15+ Typed desktop tools & OpenAI schemas
│   │   ├── execution_manager.py    # Sandboxed execution & outcome verifier
│   │   ├── task_planner.py         # Multi-step goal decomposition
│   │   ├── orchestrator.py         # Fast-path bypass & conversational turns
│   │   └── metrics.py              # LatencyTracker computing p50/p95 milestones
│   ├── nlp/
│   │   ├── language_detector.py    # Auto-detection for English, Hindi, Hinglish
│   │   ├── hinglish_normalizer.py  # Code-switching grammar & token preservation
│   │   └── intent_matcher.py       # Sub-5ms deterministic pattern matching
│   ├── ai/
│   │   ├── base_provider.py        # Abstract AI contract (generate, stream, tools)
│   │   ├── provider_manager.py     # Hybrid router & automatic fallbacks
│   │   ├── local_provider.py       # Ollama GPU inference adapter
│   │   ├── offline_provider.py     # Built-in zero-downtime offline fallback
│   │   └── openai_provider.py      # OpenAI GPT-4o integration
│   ├── voice/
│   │   ├── audio_stream.py         # Real-time microphone capture & RMS levels
│   │   ├── wake_word.py            # Voice onset & wake phrase detection
│   │   ├── speech_to_text.py       # Multilingual STT with SpeechRecognition & Whisper
│   │   ├── text_to_speech.py       # Sentence-streaming SAPI5 TTS engine
│   │   └── voice_session.py        # Hands-free loop with VAD pause detection
│   ├── desktop/
│   │   ├── windows_controller.py   # Windows API window focus, volume & lock
│   │   ├── application_launcher.py # Allowlisted application launcher
│   │   ├── file_manager.py         # Safe file operations with undo backups
│   │   └── browser_automation.py   # Web search and Playwright automation
│   ├── memory/
│   │   ├── database.py             # SQLite WAL-mode relational database
│   │   ├── task_repository.py      # Checkpointed task & subtask persistence
│   │   └── memory_service.py       # Stated facts vs inferred preferences
│   ├── services/
│   │   ├── news_service.py         # RSS-backed news & Open-Meteo weather
│   │   ├── briefing_service.py     # Synthesized morning briefing generator
│   │   ├── startup_service.py      # Windows HKCU Run registry integration
│   │   └── scheduler.py            # Background timer for morning briefings
│   └── ui/
│       ├── theme.py                # Electric cyan (#00E5FF) & dark charcoal styling
│       ├── main_window.py          # Master window with sidebar navigation
│       ├── dashboard.py            # Real-time CPU, RAM, Disk, GPU & latency telemetry
│       ├── conversation.py         # Interactive chat bubbles with tool cards
│       ├── tasks_view.py           # Task management & progress tracking
│       ├── memory_view.py          # Declarative memory inspection & export
│       └── settings.py             # Voice, language mode, AI keys, autonomy sliders
├── tests/                          # 21 automated pytest test suites
├── run_friday.bat                  # One-click Windows desktop launcher
├── run_friday.ps1                  # PowerShell native launcher
├── install_friday.bat              # One-click installation script
└── requirements.txt                # Python dependencies
```

---

## 🧪 Automated Test Suite

FRIDAY includes 21 comprehensive automated unit and integration tests covering all subsystems:

```powershell
.venv\Scripts\pytest.exe -v tests
```

**Test Coverage Summary:**
* `tests/test_foundation.py`: Config, credential redaction, path containment, SQLite WAL schemas, memory, emergency stop.
* `tests/test_ai_and_planner.py`: ProviderManager routing, VRAM recommendations, task decomposition.
* `tests/test_desktop_and_tools.py`: Tool schemas, safe file writes with undo backups, autonomy approvals.
* `tests/test_services_and_ui.py`: News and weather fetcher, morning briefing, Windows startup, UI smoke tests.
* `tests/test_multilingual_and_latency.py`: Language detection (EN/HI/Hinglish), token preservation, fast-path intent matching (<5ms), cancellations, and p50/p95 latency percentiles.

---

## ❓ Troubleshooting & FAQ

#### 1. "The term '.\run_friday.bat' is not recognized"
* **Solution:** Ensure your PowerShell terminal is in the project folder:
  ```powershell
  cd C:\Friday; .\run_friday.bat
  ```

#### 2. "I don't hear any speech output"
* Open **Settings & Security** -> Ensure **Voice & Speech Synthesis** is enabled and volume slider is above 50%.
* Verify your Windows default audio output device is connected and unmuted.

#### 3. "Microphone is not taking my voice commands"
* Click the **`🎙️ Push to Talk`** button in the header or floating HUD to verify your microphone is capturing audio.
* Check that your microphone is granted permissions under **Windows Settings -> Privacy & Security -> Microphone**.

#### 4. Automatic Launch on Windows Startup
* In FRIDAY, click **Settings & Security** -> Check **"Launch FRIDAY automatically when signing in to Windows"**. This registers FRIDAY safely in `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` without requiring administrative rights.

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).
