"""Hinglish and Multilingual Normalizer for Project FRIDAY.

Normalizes colloquial code-switching variants into canonical intent tokens while strictly
preserving file paths, technical identifiers, application names, and code syntax.
"""

import re
from typing import Dict, Tuple, List, Optional


class HinglishNormalizer:
    """Extracts semantic verbs and actions from Hindi and Hinglish utterances."""

    # Canonical semantic action mapping for common variants
    ACTION_VARIANTS: Dict[str, str] = {
        # Open / Launch
        "kholo": "OPEN",
        "khol": "OPEN",
        "khol do": "OPEN",
        "open karo": "OPEN",
        "open kar do": "OPEN",
        "start karo": "OPEN",
        "launch karo": "OPEN",
        "chalao": "OPEN",
        "chala do": "OPEN",

        # Close / Quit
        "band karo": "CLOSE",
        "band kar do": "CLOSE",
        "close karo": "CLOSE",
        "close kar do": "CLOSE",
        "hatao": "CLOSE",

        # Stop / Cancel / Negative
        "ruk jao": "CANCEL",
        "ruko": "CANCEL",
        "stop": "CANCEL",
        "cancel": "CANCEL",
        "cancel karo": "CANCEL",
        "mat karo": "CANCEL",
        "chup ho jao": "STOP_SPEAKING",
        "shant raho": "STOP_SPEAKING",
        "bolna band karo": "STOP_SPEAKING",

        # Query / Show / Tell
        "batao": "QUERY",
        "bataiye": "QUERY",
        "dikhao": "QUERY",
        "dikha do": "QUERY",
        "samjhao": "EXPLAIN",
        "check karo": "QUERY",
        "status batao": "QUERY_STATUS",

        # Volume
        "awaaz badhao": "VOLUME_UP",
        "volume badhao": "VOLUME_UP",
        "awaaz kam karo": "VOLUME_DOWN",
        "volume kam karo": "VOLUME_DOWN",
        "mute karo": "MUTE",

        # Lock
        "lock karo": "LOCK",
        "pc lock karo": "LOCK",
        "screen lock karo": "LOCK",

        # Devanagari Hindi Actions
        "खोलो": "OPEN",
        "खोलें": "OPEN",
        "खोलिए": "OPEN",
        "शुरू करो": "OPEN",
        "चालू करो": "OPEN",
        "बंद करो": "CLOSE",
        "बंद करें": "CLOSE",
        "रुक जाओ": "CANCEL",
        "रुकिए": "CANCEL",
        "बताओ": "QUERY",
        "बताइए": "QUERY",
        "दिखाओ": "QUERY",
        "दिखाइए": "QUERY",
        "समझाओ": "EXPLAIN",
        "म्यूट करो": "MUTE",
    }

    # Protected technical keywords that should NEVER be translated or modified
    PROTECTED_TOKENS = {
        "vscode", "vs code", "python", "git", "github", "cmd", "terminal",
        "powershell", "notepad", "calculator", "chrome", "edge", "explorer",
        "docker", "fastapi", "sqlite", "pytest", "pyside6", "main.py",
        "requirements.txt", "readme.md",
    }

    def extract_action(self, text: str) -> Optional[str]:
        """Match canonical action from Hinglish or Hindi utterance."""
        lower = text.lower()
        for variant, canonical in self.ACTION_VARIANTS.items():
            pattern = r"\b" + re.escape(variant) + r"\b"
            if re.search(pattern, lower):
                return canonical
        return None

    def extract_app_target(self, text: str) -> Optional[str]:
        """Detect referenced approved applications using strict word boundaries to avoid false triggers."""
        lower = text.lower()
        if re.search(r"\b(notepad|नोटपैड)\b", lower):
            return "notepad"
        if re.search(r"\b(calculator|calc|कैलकुलेटर)\b", lower) or "कैलकुलेटर" in text:
            return "calculator"
        if re.search(r"\b(vs\s*code|vscode)\b", lower):
            return "vscode"
        if re.search(r"\b(file\s*explorer|explorer|एक्सप्लोरर)\b", lower):
            return "explorer"
        if re.search(r"\b(terminal|windows\s*terminal|टर्मिनल)\b", lower):
            return "terminal"
        if re.search(r"\b(chrome|google\s*chrome|क्रोम)\b", lower):
            return "chrome"
        if re.search(r"\b(edge|msedge|microsoft\s*edge|एज)\b", lower):
            return "edge"
        return None


# Global singleton
hinglish_normalizer = HinglishNormalizer()
