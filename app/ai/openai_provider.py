"""OpenAI Provider for Project FRIDAY.

Integrates with the OpenAI API for high-reasoning tasks, coding, and structured planning.
"""

import json
import logging
from typing import List, Dict, Any, Optional, Generator
import requests

from app.ai.base_provider import BaseAIProvider, AIResponse, ToolCall
from app.security.secret_store import secret_store
from app.config import config

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseAIProvider):
    """Cloud provider adapter for OpenAI models."""

    API_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(
        self,
        default_model: Optional[str] = None,
        timeout: int = 60,
    ):
        model = default_model or config.ai.openai_model
        super().__init__(name="openai", default_model=model, timeout=timeout)

    def is_available(self) -> bool:
        """Check if an OpenAI API key is configured."""
        return secret_store.has_credential("openai")

    def _get_headers(self) -> Dict[str, str]:
        key = secret_store.get_credential("openai")
        if not key:
            raise ValueError("OpenAI API key is not configured in Windows Credential Manager or environment.")
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
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
                error="OpenAI API key is not configured.",
            )

        target_model = model or self.default_model
        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools

        try:
            resp = requests.post(
                self.API_URL,
                headers=self._get_headers(),
                json=payload,
                timeout=self.timeout,
            )

            if resp.status_code != 200:
                err_text = resp.text
                return AIResponse(
                    content="",
                    provider_name=self.name,
                    model_name=target_model,
                    error=f"OpenAI error HTTP {resp.status_code}: {err_text}",
                )

            data = resp.json()
            choice = data["choices"][0]
            msg = choice.get("message", {})
            content = msg.get("content") or ""

            tool_calls = []
            if "tool_calls" in msg and msg["tool_calls"]:
                for tc in msg["tool_calls"]:
                    fn = tc.get("function", {})
                    args = {}
                    try:
                        args = json.loads(fn.get("arguments", "{}"))
                    except Exception:
                        pass
                    tool_calls.append(
                        ToolCall(
                            id=tc.get("id", ""),
                            name=fn.get("name", ""),
                            arguments=args,
                        )
                    )

            usage = data.get("usage", {})
            return AIResponse(
                content=content,
                tool_calls=tool_calls,
                provider_name=self.name,
                model_name=target_model,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                finish_reason=choice.get("finish_reason", "stop"),
            )

        except requests.Timeout:
            return AIResponse(
                content="",
                provider_name=self.name,
                model_name=target_model,
                error=f"OpenAI request timed out after {self.timeout}s",
            )
        except Exception as e:
            return AIResponse(
                content="",
                provider_name=self.name,
                model_name=target_model,
                error=f"OpenAI request failed: {str(e)}",
            )

    def stream_generate(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Generator[str, None, AIResponse]:
        if not self.is_available():
            err = "OpenAI API key is not configured."
            yield err
            return AIResponse(
                content="",
                provider_name=self.name,
                model_name=model or self.default_model,
                error=err,
            )

        target_model = model or self.default_model
        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools

        full_content = []
        try:
            with requests.post(
                self.API_URL,
                headers=self._get_headers(),
                json=payload,
                stream=True,
                timeout=self.timeout,
            ) as resp:
                if resp.status_code != 200:
                    err = f"OpenAI HTTP error {resp.status_code}"
                    yield err
                    return AIResponse(content="", provider_name=self.name, model_name=target_model, error=err)

                for line in resp.iter_lines():
                    if line:
                        line_str = line.decode("utf-8").strip()
                        if line_str.startswith("data: "):
                            data_str = line_str[6:]
                            if data_str == "[DONE]":
                                break
                            chunk = json.loads(data_str)
                            delta = chunk["choices"][0].get("delta", {})
                            content_piece = delta.get("content", "")
                            if content_piece:
                                full_content.append(content_piece)
                                yield content_piece

            return AIResponse(
                content="".join(full_content),
                provider_name=self.name,
                model_name=target_model,
                finish_reason="stop",
            )
        except Exception as e:
            err = f"Stream failed: {e}"
            yield err
            return AIResponse(
                content="".join(full_content),
                provider_name=self.name,
                model_name=target_model,
                error=err,
            )
