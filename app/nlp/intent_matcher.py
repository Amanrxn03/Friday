"""Fast Deterministic Multilingual Intent Matcher for Project FRIDAY.

Bypasses slow LLM network roundtrips for predictable desktop, volume, system status,
application, and cancellation commands in English, Hindi, and Hinglish (<5ms latency).
"""

import re
from dataclasses import dataclass
from typing import Optional, Dict, Any

from app.nlp.language_detector import language_detector
from app.nlp.hinglish_normalizer import hinglish_normalizer
from app.config import config


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

        clean = hinglish_normalizer.normalize_wake_phrase(text.strip())
        lower = clean.lower()
        lang = language_detector.detect(clean)

        # Strip conversational fillers, wake phrases, and polite prefixes
        prefix_pattern = r"^(hey\s*friday|friday|suno\s*friday|frida|hello\s*friday|hi\s*friday|hey\s*kriti|kriti|suno\s*kriti|hello\s*kriti|hi\s*kriti|please|can\s*you|could\s*you|kripya|bhai|yaar|zara)\s*[,:\s]+"
        norm_clean = re.sub(prefix_pattern, "", clean, flags=re.I).strip()
        norm_lower = norm_clean.lower() if norm_clean else lower

        # 1. Stop / Cancel / Negative Commands (Top Priority)
        cancel_patterns = [
            r"\b(stop|halt|cancel|abort)\b",
            r"\b(ruk\s*jao|ruko|rukna|mat\s*karo|cancel\s*karo)\b",
            r"\b(don'?t\s*do\s*that|stop\s*it|nevermind)\b",
            r"\b(रुक\s*जाओ|रुकिए|बंद\s*करो|मत\s*करो)\b",
            r"\b(chup\s*ho\s*jao|shant\s*raho)\b",
        ]
        for pat in cancel_patterns:
            if re.search(pat, lower) or re.search(pat, norm_lower):
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

        # 2. Current Time & Date (<1ms instant response)
        time_patterns = [
            r"\b(what\s*time\s*is\s*it|what'?s\s*the\s*time|current\s*time)\b",
            r"\b(time\s*kya\s*hai|samay\s*kya\s*hai|kitne\s*baje\s*hain|time\s*batao)\b",
            r"\b(समय\s*क्या\s*है|कितने\s*बजे\s*हैं|टाइम\s*क्या\s*हुआ)\b",
            r"\b(what\s*is\s*today'?s\s*date|today'?s\s*date|what\s*day\s*is\s*it|current\s*date)\b",
            r"\b(aaj\s*ki\s*tarikh|tarikh\s*kya\s*hai|aaj\s*kaun\s*sa\s*din\s*hai)\b",
        ]
        for pat in time_patterns:
            if re.search(pat, lower) or re.search(pat, norm_lower):
                import datetime
                now = datetime.datetime.now()
                t_str = now.strftime("%I:%M %p")
                d_str = now.strftime("%A, %B %d")
                return ParsedIntent(
                    tool_name="get_current_time",
                    tool_args={},
                    confidence=0.99,
                    detected_language=lang,
                    conversational_replies={
                        "en": f"The current time is {t_str} on {d_str}.",
                        "hi": f"अभी समय {t_str} है और आज {d_str} है।",
                        "hinglish": f"Abhi time {t_str} ho raha hai, {d_str}.",
                    },
                )

        # 2b. Voice Profile & Custom Voice Cloning (Kriti's Voice)
        voice_select_patterns = [
            r"\b(use|select|set|switch\s*to)?\s*(kriti'?s?\s*voice|her\s*voice|kriti\s*ki\s*awaaz)\b",
            r"\b(i\s*want\s*to\s*use\s*(her|kriti'?s?)\s*voice)\b",
            r"\b(kriti\s*ki\s*awaaz\s*(use|set|chahiye|lagao))\b",
        ]
        for pat in voice_select_patterns:
            if re.search(pat, lower) or re.search(pat, norm_lower):
                return ParsedIntent(
                    tool_name="set_voice_profile",
                    tool_args={"profile_id": "kriti"},
                    confidence=0.99,
                    detected_language=lang,
                    conversational_replies={
                        "en": "I have selected Kriti's voice for you. I will now speak with her voice profile.",
                        "hi": "मैंने कृति की आवाज़ चुन ली है। अब मैं इसी आवाज़ में बात करूँगी।",
                        "hinglish": "Kriti ki voice select kar li hai. Ab main unki voice profile use karungi.",
                    },
                )

        voice_play_patterns = [
            r"\b(play|listen\s*to|sunao)\s*(kriti'?s?\s*voice|sample|her\s*voice|recording)\b",
            r"\b(kriti\s*ki\s*awaaz\s*(sunao|play\s*karo))\b",
        ]
        for pat in voice_play_patterns:
            if re.search(pat, lower) or re.search(pat, norm_lower):
                return ParsedIntent(
                    tool_name="play_voice_sample",
                    tool_args={},
                    confidence=0.99,
                    detected_language=lang,
                    conversational_replies={
                        "en": "Playing Kriti's voice audio sample now.",
                        "hi": "कृति की आवाज़ का ऑडियो सैंपल चलाया जा रहा है।",
                        "hinglish": "Kriti ka audio sample play kar rahi hoon.",
                    },
                )

        # 3. Workstation Lock
        lock_patterns = [
            r"\b(lock\s*(the|my)?\s*(workstation|pc|computer|screen))\b",
            r"\b(pc|screen|system|workstation)?\s*lock\s*(karo|kar\s*do|kijiye|kar)?\b",
            r"\b(स्क्रीन\s*लॉक\s*करो|कंप्यूटर\s*लॉक\s*करो|लॉक\s*करो)\b",
        ]
        for pat in lock_patterns:
            if re.search(pat, lower) or re.search(pat, norm_lower):
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
        vol_match = re.search(r"\b(volume|awaaz|sound)\s*(to|pe|par)?\s*(\d{1,3})\b", lower) or re.search(r"\b(volume|awaaz|sound)\s*(to|pe|par)?\s*(\d{1,3})\b", norm_lower)
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

        if re.search(r"\b(mute|sound\s*band\s*karo|awaaz\s*band\s*karo)\b", lower) or re.search(r"\b(mute|sound\s*band\s*karo|awaaz\s*band\s*karo)\b", norm_lower):
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

        # 5. Popular Websites (YouTube, GitHub, Google, etc.)
        website_map = {
            "youtube": ("https://www.youtube.com", "YouTube", "यूट्यूब"),
            "github": ("https://www.github.com", "GitHub", "गिटहब"),
            "google": ("https://www.google.com", "Google", "गूगल"),
            "chatgpt": ("https://chatgpt.com", "ChatGPT", "चैटजीपीटी"),
            "reddit": ("https://www.reddit.com", "Reddit", "रेडिट"),
        }
        for site_key, (site_url, site_name, hi_site_name) in website_map.items():
            if site_key in lower or site_key in norm_lower or hi_site_name in clean:
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

        # 6. Launch Approved Applications
        app_target = hinglish_normalizer.extract_app_target(norm_clean) or hinglish_normalizer.extract_app_target(clean)
        action = hinglish_normalizer.extract_action(norm_clean) or hinglish_normalizer.extract_action(clean)
        is_direct_app_name = norm_lower in ("notepad", "calculator", "vscode", "explorer", "terminal", "chrome", "edge")

        if app_target and (action == "OPEN" or is_direct_app_name or "खोलो" in lower or "खोल" in lower or re.search(r"\b(open|launch|start|kholo|chalao)\b", lower) or re.search(r"\b(open|launch|start|kholo|chalao)\b", norm_lower)):
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

        # 7. System Status / Battery / Telemetry
        status_patterns = [
            r"\b(system\s*status|specs|hardware\s*info|cpu\s*usage|ram\s*usage)\b",
            r"\b(battery\s*kitni\s*hai|battery\s*check\s*karo|system\s*check\s*karo|ram\s*kitna\s*hai)\b",
            r"\b(सिस्टम\s*स्टेटस|बैटरी\s*कितनी\s*है|रैम\s*दिखाओ)\b",
        ]
        for pat in status_patterns:
            if re.search(pat, lower) or re.search(pat, norm_lower):
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

        # 8. Morning Briefing / News
        if re.search(r"\b(briefing|morning\s*briefing|aaj\s*ka\s*briefing|news\s*batao|khabar\s*batao)\b", lower) or re.search(r"\b(briefing|morning\s*briefing|aaj\s*ka\s*briefing|news\s*batao|khabar\s*batao)\b", norm_lower):
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

        # 9. Conversational Greetings & Identity (Fallback for pure conversational turns)
        if re.search(r"\b(who\s*are\s*you|what\s*is\s*your\s*name|tum\s*kaun\s*ho|kaun\s*ho\s*tum|tumhara\s*naam\s*kya\s*hai|naam\s*kya\s*hai)\b", lower) or re.search(r"\b(who\s*are\s*you|what\s*is\s*your\s*name|tum\s*kaun\s*ho|kaun\s*ho\s*tum|tumhara\s*naam\s*kya\s*hai|naam\s*kya\s*hai)\b", norm_lower):
            nick = config.assistant_nickname or "Kriti"
            return ParsedIntent(
                tool_name="get_system_status",
                tool_args={},
                confidence=0.98,
                detected_language=lang,
                conversational_replies={
                    "en": f"I am FRIDAY, and you can also call me {nick}! Your personal AI desktop companion for Windows 11.",
                    "hi": f"मैं फ्राइडे हूँ, और आप मुझे {nick} भी बुला सकते हैं! आपकी व्यक्तिगत AI डेस्कटॉप साथी।",
                    "hinglish": f"Main FRIDAY hoon, aur aap mujhe {nick} bhi bula sakte hain! Aapki personal AI desktop assistant.",
                },
            )

        greeting_pattern = r"\b(hi|hello|hey|namaste|नमस्ते|kaise\s*ho|how\s*are\s*you|kya\s*haal\s*hai|wake\s*up|uth\s*jao|jago|are\s*you\s*awake|are\s*you\s*there)\b"
        if (
            re.search(greeting_pattern, norm_lower)
            or re.search(greeting_pattern, lower)
            or re.search(r"\b(hi|hello|hey|namaste)\s*(friday|kriti)?\b", lower)
            or norm_lower in ("kriti", "friday")
            or lower in ("kriti", "friday")
        ):
            user_name = getattr(config, "user_name", "Aman") or "Aman"
            is_hey = bool(re.search(r"\b(hey|hi)\b", lower) or re.search(r"\b(hey|hi)\b", norm_lower))
            salutation = "Hey" if is_hey else "Hello"
            return ParsedIntent(
                tool_name="get_system_status",
                tool_args={},
                confidence=0.98,
                detected_language=lang,
                conversational_replies={
                    "en": f"{salutation} {user_name}!",
                    "hi": f"नमस्ते {user_name}!",
                    "hinglish": f"{salutation} {user_name}!",
                },
            )

        # No deterministic match: return None so the request routes to the LLM reasoning planner
        return None


# Global singleton
intent_matcher = IntentMatcher()
