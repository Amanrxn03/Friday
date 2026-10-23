"""Built-in Local Offline Fallback Provider for Project FRIDAY.

Guarantees 100% conversational continuity and desktop tool execution even when
external cloud API keys are not yet configured or local models are downloading.
"""

import logging
from typing import List, Dict, Any, Optional, Generator

from app.ai.base_provider import BaseAIProvider, AIResponse, ToolCall
from app.nlp.language_detector import language_detector
from app.nlp.intent_matcher import intent_matcher

logger = logging.getLogger(__name__)


class OfflineFallbackProvider(BaseAIProvider):
    """Zero-dependency local fallback engine that preserves voice, language, and tool execution."""

    def __init__(self):
        super().__init__(name="offline", default_model="friday-local-engine", timeout=1)

    def is_available(self) -> bool:
        """Always available as a built-in safety net."""
        return True

    def generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AIResponse:
        # Get the latest user utterance
        user_text = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_text = m.get("content", "").strip()
                break

        lang = language_detector.detect(user_text)

        # 1. Check if the utterance matches any desktop tool intent
        fast_intent = intent_matcher.match_intent(user_text)
        tool_calls: List[ToolCall] = []

        if fast_intent:
            tool_calls.append(
                ToolCall(
                    id="call_offline_0",
                    name=fast_intent.tool_name,
                    arguments=fast_intent.tool_args,
                )
            )
            reply = fast_intent.conversational_replies.get(lang, "Executing requested command.")
            return AIResponse(
                content=reply,
                tool_calls=tool_calls,
                provider_name="offline",
                model_name=self.default_model,
            )

        # 2. General conversational fallback responses tailored to language
        if lang == "hi":
            content = (
                "नमस्ते! मैं फ्राइडे हूँ। आपके NVIDIA RTX 4070 GPU पर लोकल Ollama AI मॉडल बैकग्राउंड "
                "में लोड हो रहा है। मैं आपके ऐप्स खोल सकती हूँ, वॉल्यूम बदल सकती हूँ, पीसी लॉक कर सकती हूँ, "
                "और सिस्टम स्टेटस चेक कर सकती हूँ। बताइए, क्या सहायता करूँ?"
            )
        elif lang == "hinglish":
            content = (
                "Main sun rahi hoon! Aapke NVIDIA RTX 4070 GPU ke liye Ollama local AI model background "
                "mein configure ho raha hai. Tab tak main aapke apps open karna, files check karna, "
                "volume adjust karna aur PC controls execute kar sakti hoon. Bolo, kya kaam karna hai?"
            )
        else:
            content = (
                "I'm here! Ollama's local model is currently being prepared for your NVIDIA RTX 4070 GPU "
                "in the background. In the meantime, I can launch your applications, adjust volume, "
                "check system hardware, read files, and lock your workstation. What would you like me to do?"
            )

        return AIResponse(
            content=content,
            tool_calls=[],
            provider_name="offline",
            model_name=self.default_model,
        )

    def stream_generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
    ) -> Generator[str, None, AIResponse]:
        res = self.generate(messages, tools=tools, model=model)
        for word in res.content.split():
            yield word + " "
        return res
