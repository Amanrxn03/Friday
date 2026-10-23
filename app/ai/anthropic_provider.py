"""Anthropic Claude Provider for Project FRIDAY.

Integrates with the Anthropic Messages API (claude-3-5-sonnet, claude-3-haiku).
"""

import json
import logging
from typing import List, Dict, Any, Optional, Generator
import requests

from app.ai.base_provider import BaseAIProvider, AIResponse, ToolCall
from app.security.secret_store import secret_store
from app.config import config

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseAIProvider):
    """Cloud provider adapter for Anthropic Claude models."""

    API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, default_model: Optional[str] = None, timeout: int = 60):
        model = default_model or config.ai.anthropic_model
        super().__init__(name="anthropic", default_model=model, timeout=timeout)

    def is_available(self) -> bool:
        return secret_store.has_credential("anthropic")

    def _get_headers(self) -> Dict[str, str]:
        key = secret_store.get_credential("anthropic")
        if not key:
            raise ValueError("Anthropic API key is not configured.")
        return {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

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
                error="Anthropic API key is not configured.",
            )

        target_model = model or self.default_model

        # Anthropic separates system prompt from conversation messages
        system_text = ""
        user_assistant_messages = []
        for m in messages:
            if m.get("role") == "system":
                system_text = m.get("content", "")
            else:
                user_assistant_messages.append({"role": m.get("role"), "content": m.get("content", "")})

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": user_assistant_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_text:
            payload["system"] = system_text

        try:
            resp = requests.post(
                self.API_URL,
                headers=self._get_headers(),
                json=payload,
                timeout=self.timeout,
            )

            if resp.status_code != 200:
                return AIResponse(
                    content="",
                    provider_name=self.name,
                    model_name=target_model,
                    error=f"Anthropic error HTTP {resp.status_code}: {resp.text}",
                )

            data = resp.json()
            content_blocks = data.get("content", [])
            text_parts = [b["text"] for b in content_blocks if b.get("type") == "text"]
            full_text = "".join(text_parts)

            usage = data.get("usage", {})
            return AIResponse(
                content=full_text,
                provider_name=self.name,
                model_name=target_model,
                prompt_tokens=usage.get("input_tokens", 0),
                completion_tokens=usage.get("output_tokens", 0),
                finish_reason=data.get("stop_reason", "stop"),
            )

        except Exception as e:
            return AIResponse(
                content="",
                provider_name=self.name,
                model_name=target_model,
                error=f"Anthropic request failed: {str(e)}",
            )

    def stream_generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Generator[str, None, AIResponse]:
        res = self.generate(messages, tools, model, temperature, max_tokens)
        if res.content:
            yield res.content
        elif res.error:
            yield res.error
        return res
