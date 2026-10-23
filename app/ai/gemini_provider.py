"""Google Gemini Provider for Project FRIDAY.

Integrates with the Google Gemini API (gemini-2.0-flash / gemini-1.5-pro).
"""

import json
import logging
from typing import List, Dict, Any, Optional, Generator
import requests

from app.ai.base_provider import BaseAIProvider, AIResponse, ToolCall
from app.security.secret_store import secret_store
from app.config import config

logger = logging.getLogger(__name__)


class GeminiProvider(BaseAIProvider):
    """Cloud provider adapter for Google Gemini models."""

    def __init__(self, default_model: Optional[str] = None, timeout: int = 60):
        model = default_model or config.ai.gemini_model
        super().__init__(name="gemini", default_model=model, timeout=timeout)

    def is_available(self) -> bool:
        return secret_store.has_credential("gemini")

    def generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AIResponse:
        if not self.is_available():
            return AIResponse(
                content="",
                provider_name=self.name,
                model_name=model or self.default_model,
                error="Gemini API key is not configured.",
            )

        api_key = secret_store.get_credential("gemini")
        target_model = model or self.default_model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={api_key}"

        # Convert messages format to Gemini contents
        contents = []
        system_instruction = None
        for m in messages:
            role = m.get("role", "user")
            text = m.get("content", "")
            if role == "system":
                system_instruction = {"parts": [{"text": text}]}
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": text}]})
            else:
                contents.append({"role": "user", "parts": [{"text": text}]})

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            if resp.status_code != 200:
                return AIResponse(
                    content="",
                    provider_name=self.name,
                    model_name=target_model,
                    error=f"Gemini error HTTP {resp.status_code}: {resp.text}",
                )

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return AIResponse(
                    content="",
                    provider_name=self.name,
                    model_name=target_model,
                    error="No candidates returned from Gemini.",
                )

            parts = candidates[0].get("content", {}).get("parts", [])
            text_result = "".join([p.get("text", "") for p in parts])

            usage = data.get("usageMetadata", {})
            return AIResponse(
                content=text_result,
                provider_name=self.name,
                model_name=target_model,
                prompt_tokens=usage.get("promptTokenCount", 0),
                completion_tokens=usage.get("candidatesTokenCount", 0),
                finish_reason="stop",
            )
        except Exception as e:
            return AIResponse(
                content="",
                provider_name=self.name,
                model_name=target_model,
                error=f"Gemini request failed: {str(e)}",
            )

    def stream_generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Generator[str, None, AIResponse]:
        # For simplicity and reliability with REST, delegate to generate and yield full content
        res = self.generate(messages, tools, model, temperature, max_tokens)
        if res.content:
            yield res.content
        elif res.error:
            yield res.error
        return res
