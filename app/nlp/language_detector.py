"""Multilingual Language Detector for Project FRIDAY.

Detects English, Hindi (Devanagari script), and Hinglish (Latin-script Hindi-English
code-switching) with high accuracy and zero cloud dependency.
"""

import re
from typing import Set, Tuple


class LanguageDetector:
    """Detects English, Hindi, and Hinglish in text prompts."""

    # Unicode range for Devanagari script: U+0900 to U+097F
    DEVANAGARI_PATTERN = re.compile(r"[\u0900-\u097F]")

    # Common Roman-script Hindi marker tokens indicative of Hinglish code-switching
    HINGLISH_MARKERS: Set[str] = {
        "mera", "meri", "mere", "tera", "teri", "tere", "apna", "apni", "apne",
        "kholo", "khol", "karo", "kar", "karna", "karein", "kijiye",
        "batao", "bataiye", "dikhao", "dikha", "samjhao", "sunao",
        "kaunsi", "kaunsa", "kya", "kaise", "kyun", "kab", "kahan", "kitna", "kitni",
        "hai", "hain", "tha", "thi", "hoga", "hogi", "honge", "maine", "tune",
        "pe", "par", "mein", "se", "ko", "ke", "liye", "aur", "ya", "bhi", "toh", "phir",
        "kal", "aaj", "abhi", "baad", "pehle",
        "kaam", "ruk", "jao", "mat", "chalao", "band", "bhej",
        "suno", "bolo", "achha", "theek",
    }

    # Distinctive English function words to cross-reference
    ENGLISH_STOPS: Set[str] = {
        "the", "a", "an", "is", "are", "was", "were", "what", "how", "why", "when",
        "where", "who", "which", "this", "that", "these", "those", "my", "your",
        "his", "her", "their", "our", "and", "or", "but", "if", "then", "with",
        "without", "for", "from", "in", "on", "at", "by", "to", "do", "does", "did",
        "have", "has", "had", "can", "could", "will", "would", "should", "it", "its"
    }

    def detect(self, text: str) -> str:
        """Detect language of the utterance.

        Returns:
            'hi' for Devanagari Hindi
            'hinglish' for code-switched Hindi-English in Latin script
            'en' for English
        """
        if not text or not text.strip():
            return "en"

        clean = text.strip()

        # 1. Check for Devanagari characters
        devanagari_count = len(self.DEVANAGARI_PATTERN.findall(clean))
        total_letters = len([c for c in clean if c.isalpha()])

        if total_letters > 0 and (devanagari_count / total_letters) > 0.25:
            return "hi"

        # 2. Tokenize lowercase words to check for Hinglish markers
        words = [re.sub(r"[^\w]", "", w.lower()) for w in clean.split()]
        words = [w for w in words if w]

        if not words:
            return "en"

        hinglish_hits = sum(1 for w in words if w in self.HINGLISH_MARKERS)
        english_hits = sum(1 for w in words if w in self.ENGLISH_STOPS)

        # Hinglish requires presence of Hindi markers; if strong English syntax is present,
        # require at least 1 clear Hinglish marker and not predominantly pure English
        if hinglish_hits >= 1 and (english_hits == 0 or hinglish_hits >= english_hits or hinglish_hits >= 2):
            return "hinglish"
        elif hinglish_hits >= 1 and english_hits <= 1:
            return "hinglish"

        return "en"

    def get_language_display_name(self, code: str) -> str:
        names = {
            "en": "English",
            "hi": "Hindi (हिंदी)",
            "hinglish": "Hinglish (हिंग्लिश)",
        }
        return names.get(code, "English")


# Global singleton
language_detector = LanguageDetector()
