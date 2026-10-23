"""Multilingual Natural Language Processing and Intent Engine for Project FRIDAY.

Supports English, Hindi (Devanagari), and Roman-script Hinglish code-switching.
"""

from app.nlp.language_detector import LanguageDetector, language_detector
from app.nlp.hinglish_normalizer import HinglishNormalizer, hinglish_normalizer
from app.nlp.intent_matcher import IntentMatcher, intent_matcher, ParsedIntent

__all__ = [
    "LanguageDetector",
    "language_detector",
    "HinglishNormalizer",
    "hinglish_normalizer",
    "IntentMatcher",
    "intent_matcher",
    "ParsedIntent",
]
