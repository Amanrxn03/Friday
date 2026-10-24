"""Fast Deterministic Multilingual Intent Matcher for Project FRIDAY.

Bypasses slow LLM network roundtrips for predictable desktop, volume, system status,
application, and cancellation commands in English, Hindi, and Hinglish (<5ms latency).
"""

import re
from dataclasses import dataclass
from typing import Optional, Dict, Any

from app.nlp.language_detector import language_detector
from app.nlp.hinglish_normalizer import hinglish_normalizer


@dataclass
class ParsedIntent:
    tool_name: str
    tool_args: Dict[str, Any]
    confidence: float
    detected_language: str
    is_cancellation: bool = False
    conversational_replies: Dict[str, str] = None  # keyed by 'en', 'hi', 'hinglish'


class IntentMatcher:
    """Matches common desktop and system intents deterministically without calling an LLM."""

    def match_intent(self, text: str) -> Optional[ParsedIntent]:
        """Attempt to match a deterministic command. Returns ParsedIntent or None."""
        if not text or not text.strip():
            return None

        clean = text.strip()
        lower = clean.lower()
        lang = language_detector.detect(clean)

        # 1. Stop / Cancel / Negative Commands (Top Priority)
        cancel_patterns = [
            r"\b(stop|halt|cancel|abort)\b",
            r"\b(ruk\s*jao|ruko|rukna|mat\s*karo|cancel\s*karo)\b",
            r"\b(don'?t\s*do\s*that|stop\s*it|nevermind)\b",
            r"\b(रुक\s*जाओ|रुकिए|बंद\s*करो|मत\s*करो)\b",
            r"\b(chup\s*ho\s*jao|shant\s*raho)\b",
        ]
        for pat in cancel_patterns:
            if re.search(pat, lower):
                return ParsedIntent(
                    tool_name="emergency_stop",
                    tool_args={"reason": "User cancellation command"},
                    confidence=1.0,
                    detected_language=lang,
                    is_cancellation=True,
                    conversational_replies={
                        "en": "Stopped. I've cancelled the current action.",
                        "hi": "रोक दिया गया। चालू काम रद्द कर दिया गया है।",
                        "hinglish": "Ruk gayi. Current action cancel kar diya hai.",
                    },
                )

        # 2. System Status / Battery / Telemetry
        status_patterns = [
            r"\b(system\s*status|specs|hardware\s*info|cpu\s*usage|ram\s*usage)\b",
            r"\b(battery\s*kitni\s*hai|battery\s*check\s*karo|system\s*check\s*karo|ram\s*kitna\s*hai)\b",
            r"\b(सिस्टम\s*स्टेटस|बैटरी\s*कितनी\s*है|रैम\s*दिखाओ)\b",
        ]
        for pat in status_patterns:
            if re.search(pat, lower):
                return ParsedIntent(
                    tool_name="get_system_status",
                    tool_args={},
                    confidence=0.95,
                    detected_language=lang,
                    conversational_replies={
                        "en": "Checking your system hardware telemetry.",
                        "hi": "सिस्टम हार्डवेयर की जांच की जा रही है।",
                        "hinglish": "System telemetry check kar rahi hoon.",
                    },
                )

        # 3. Workstation Lock
        lock_patterns = [
            r"\b(lock\s*(the)?\s*(workstation|pc|computer|screen))\b",
            r"\b(pc|screen|system|workstation)?\s*lock\s*(karo|kar\s*do|kijiye)\b",
            r"\b(स्क्रीन\s*लॉक\s*करो|कंप्यूटर\s*लॉक\s*करो|लॉक\s*करो)\b",
        ]
        for pat in lock_patterns:
            if re.search(pat, lower):
                return ParsedIntent(
                    tool_name="lock_workstation",
                    tool_args={},
                    confidence=1.0,
                    detected_language=lang,
                    conversational_replies={
                        "en": "Locking your workstation now.",
                        "hi": "आपका कंप्यूटर लॉक किया जा रहा है।",
                        "hinglish": "Workstation lock kar rahi hoon.",
                    },
                )

        # 4. Volume Adjustment
        vol_match = re.search(r"\b(volume|awaaz|sound)\s*(to|pe|par)?\s*(\d{1,3})\b", lower)
        if vol_match:
            vol_val = int(vol_match.group(3))
            return ParsedIntent(
                tool_name="adjust_system_volume",
                tool_args={"level_percent": vol_val},
                confidence=0.98,
                detected_language=lang,
                conversational_replies={
                    "en": f"Setting system volume to {vol_val} percent.",
                    "hi": f"सिस्टम वॉल्यूम {vol_val} प्रतिशत सेट किया जा रहा है।",
                    "hinglish": f"Volume {vol_val}% pe set kar diya hai.",
                },
            )

        if re.search(r"\b(mute|sound\s*band\s*karo|awaaz\s*band\s*karo)\b", lower):
            return ParsedIntent(
                tool_name="adjust_system_volume",
                tool_args={"level_percent": 0},
                confidence=0.95,
                detected_language=lang,
                conversational_replies={
                    "en": "Muted system audio.",
                    "hi": "सिस्टम ऑडियो म्यूट कर दिया गया है।",
                    "hinglish": "System audio mute kar diya hai.",
                },
            )

        # 5. Launch Approved Applications
        app_target = hinglish_normalizer.extract_app_target(clean)
        action = hinglish_normalizer.extract_action(clean)
        if app_target and (action == "OPEN" or "खोलो" in lower or "खोल" in lower or re.search(r"\b(open|launch|start|kholo|chalao)\b", lower)):
            display_names = {
                "notepad": "Notepad",
                "calculator": "Calculator",
                "vscode": "Visual Studio Code",
                "explorer": "File Explorer",
                "terminal": "Windows Terminal",
                "chrome": "Google Chrome",
                "edge": "Microsoft Edge",
            }
            d_name = display_names.get(app_target, app_target)
            return ParsedIntent(
                tool_name="launch_application",
                tool_args={"app_alias": app_target},
                confidence=0.98,
                detected_language=lang,
                conversational_replies={
                    "en": f"Launching {d_name} for you.",
                    "hi": f"{d_name} खोला जा रहा है।",
                    "hinglish": f"{d_name} open kar rahi hoon.",
                },
            )

        # 6. Popular Websites (YouTube, GitHub, Google, etc.)
        website_map = {
            "youtube": ("https://www.youtube.com", "YouTube", "यूट्यूब"),
            "github": ("https://www.github.com", "GitHub", "गिटहब"),
            "google": ("https://www.google.com", "Google", "गूगल"),
            "chatgpt": ("https://chatgpt.com", "ChatGPT", "चैटजीपीटी"),
            "reddit": ("https://www.reddit.com", "Reddit", "रेडिट"),
        }
        for site_key, (site_url, site_name, hi_site_name) in website_map.items():
            if site_key in lower or hi_site_name in clean:
                return ParsedIntent(
                    tool_name="open_website",
                    tool_args={"url": site_url},
                    confidence=0.98,
                    detected_language=lang,
                    conversational_replies={
                        "en": f"Opening {site_name} in your browser.",
                        "hi": f"{site_name} आपके ब्राउज़र में खोला जा रहा है।",
                        "hinglish": f"{site_name} browser mein open kar rahi hoon.",
                    },
                )

        # 7. Morning Briefing / News
        if re.search(r"\b(briefing|morning\s*briefing|aaj\s*ka\s*briefing|news\s*batao|khabar\s*batao)\b", lower):
            return ParsedIntent(
                tool_name="get_briefing",
                tool_args={},
                confidence=0.95,
                detected_language=lang,
                conversational_replies={
                    "en": "Here is your morning briefing and news highlights.",
                    "hi": "यह रहा आपका आज का मॉर्निंग ब्रीफिंग।",
                    "hinglish": "Yeh raha aaj ka morning briefing aur news updates.",
                },
            )

        # No deterministic match: return None so the request routes to the LLM reasoning planner
        return None


# Global singleton
intent_matcher = IntentMatcher()
