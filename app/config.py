"""Application Configuration for Project FRIDAY.

Loads validated configuration from environment variables with sensible, secure defaults.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class AutonomyMode(str, Enum):
    """Execution autonomy modes for FRIDAY."""
    SUGGEST = "SUGGEST"                          # Mode 1: Recommends actions, waits for user approval
    APPROVED_AUTONOMY = "APPROVED_AUTONOMY"      # Mode 2: Executes low-risk reversible actions independently
    CONFIRM_HIGH_IMPACT = "CONFIRM_HIGH_IMPACT"  # Mode 3: Requires explicit approval for all consequential actions


@dataclass
class PathPolicyConfig:
    """Restricts file and execution tools to authorized directory trees."""
    allowed_roots: List[Path] = field(default_factory=lambda: [
        Path(os.environ.get("FRIDAY_WORKSPACE", "c:\\Friday")).resolve(),
        Path(os.path.expanduser("~\\Documents\\FRIDAY")).resolve(),
    ])
    denied_patterns: List[str] = field(default_factory=lambda: [
        "Windows\\System32",
        "Windows\\SysWOW64",
        "Program Files",
        ".git",
        ".env",
    ])


@dataclass
class AIProviderConfig:
    """Settings for AI providers."""
    default_provider: str = os.getenv("FRIDAY_DEFAULT_PROVIDER", "ollama")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_default_model: str = os.getenv("OLLAMA_DEFAULT_MODEL", "llama3.2:latest")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
    request_timeout_seconds: int = int(os.getenv("FRIDAY_AI_TIMEOUT", "60"))
    max_tokens: int = int(os.getenv("FRIDAY_MAX_TOKENS", "4096"))
    monthly_budget_usd: float = float(os.getenv("FRIDAY_MONTHLY_BUDGET", "50.0"))


@dataclass
class VoiceConfig:
    """Settings for speech-to-text, wake-word, and text-to-speech."""
    enabled: bool = os.getenv("FRIDAY_VOICE_ENABLED", "true").lower() == "true"
    wake_word: str = os.getenv("FRIDAY_WAKE_WORD", "Hey Friday, Hey Kriti")
    provider: str = os.getenv("FRIDAY_VOICE_PROVIDER", "local_sapi")  # local_sapi, cloud_openai, elevenlabs_clone
    voice_profile: str = os.getenv("FRIDAY_VOICE_PROFILE", "kriti")   # kriti, heera, zira, david
    custom_voice_path: str = os.getenv("FRIDAY_CUSTOM_VOICE_PATH", r"c:\Friday\app\assets\custom_voices\kriti.wav")
    custom_voice_name: str = os.getenv("FRIDAY_CUSTOM_VOICE_NAME", "Kriti's Voice")
    elevenlabs_voice_id: Optional[str] = os.getenv("ELEVENLABS_VOICE_ID", None)
    speech_rate: int = int(os.getenv("FRIDAY_SPEECH_RATE", "185"))
    volume: float = float(os.getenv("FRIDAY_SPEECH_VOLUME", "0.9"))
    push_to_talk: bool = os.getenv("FRIDAY_PUSH_TO_TALK", "false").lower() == "true"
    microphone_index: Optional[int] = None
    input_sample_rate: int = 16000
    vad_energy_threshold: float = 0.015


@dataclass
class BriefingConfig:
    """Settings for daily briefing and news fetcher."""
    enabled: bool = os.getenv("FRIDAY_NEWS_ENABLED", "true").lower() == "true"
    briefing_time: str = os.getenv("FRIDAY_BRIEFING_TIME", "08:30")
    quiet_hours_start: str = os.getenv("FRIDAY_QUIET_HOURS_START", "22:00")
    quiet_hours_end: str = os.getenv("FRIDAY_QUIET_HOURS_END", "07:00")
    categories: List[str] = field(default_factory=lambda: [
        "India National",
        "World Headlines",
        "AI & Technology",
        "Science & Space",
        "Cybersecurity",
    ])
    weather_city: str = os.getenv("FRIDAY_WEATHER_LOCATION", "Bengaluru")


@dataclass
class FridayConfig:
    """Master configuration for the FRIDAY application."""
    app_name: str = "FRIDAY"
    assistant_nickname: str = os.getenv("FRIDAY_NICKNAME", "Kriti")
    version: str = "1.0.0"
    base_dir: Path = Path(__file__).resolve().parent.parent
    data_dir: Path = base_dir / "data"
    logs_dir: Path = base_dir / "logs"
    database_path: Path = data_dir / "friday.db"
    autonomy_mode: AutonomyMode = AutonomyMode.APPROVED_AUTONOMY
    ai: AIProviderConfig = field(default_factory=AIProviderConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    briefing: BriefingConfig = field(default_factory=BriefingConfig)
    paths: PathPolicyConfig = field(default_factory=PathPolicyConfig)
    log_level: str = os.getenv("FRIDAY_LOG_LEVEL", "INFO")
    require_confirmation_deletes: bool = True
    require_confirmation_exec: bool = True

    def ensure_directories(self) -> None:
        """Create necessary data, log, and workspace directories."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        for root in self.paths.allowed_roots:
            root.mkdir(parents=True, exist_ok=True)


# Global configuration singleton
config = FridayConfig()
